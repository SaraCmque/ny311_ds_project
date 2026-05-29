import sys
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F, Window

# ─────────────────────────────────────────────────────────────────
# PROYECTO #2 — JOB DE SPLIT TEMPORAL POR PERCENTILES (70/15/15)
#
# CAMBIO CLAVE vs Proyecto #1:
#   Antes: randomSplit([0.70,0.15,0.15]) -> mezclaba fechas (leakage temporal)
#   Ahora: split TEMPORAL ORDENADO -> train=70% mas antiguo,
#          val=15% intermedio, test=15% mas reciente.
#
#   Respeta temporalidad (train siempre antes que test) Y mantiene
#   las proporciones exactas 70/15/15.
# ─────────────────────────────────────────────────────────────────
if "--JOB_NAME" in sys.argv:
    args = getResolvedOptions(sys.argv, ["JOB_NAME"])
else:
    args = {"JOB_NAME": "jupyter_interactive_job"}

sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

PATH_SILVER = "s3://proyect-ny311/silver/ny311/"
PATH_SPLITS = "s3://proyect-ny311/gold/splits_v2/ny311/"   # carpeta NUEVA (_v2)

# 1. Leer Silver
print("1. Leyendo Silver...")
df = spark.read.parquet(PATH_SILVER)
print(f"   Filas Silver: {df.count():,}")

# 2. Calcular dias_resolucion, timestamp y fecha, filtrar validos
print("\n2. Calculando dias_resolucion y filtrando validos...")
df = df.withColumn(
    "created_ts", F.to_timestamp("Created Date", "yyyy-MM-dd HH:mm:ss")
).withColumn(
    "dias_resolucion", F.datediff(F.col("Closed Date"), F.col("Created Date"))
).withColumn(
    "fecha_creacion", F.to_date(F.col("created_ts"))
)

total_antes = df.count()
df = df.filter(
    F.col("dias_resolucion").isNotNull() &
    (F.col("dias_resolucion") >= 0) &
    F.col("created_ts").isNotNull()
)
total_despues = df.count()
print(f"   Total original : {total_antes:,}")
print(f"   Validos        : {total_despues:,}")

# 3. Inspeccion del rango temporal
print("\n3. Inspeccionando rango temporal...")
df.select(
    F.min("created_ts").alias("fecha_min"),
    F.max("created_ts").alias("fecha_max")
).show(truncate=False)

# 4. Split temporal por percentiles (70/15/15)
print("\n4. Calculando puntos de corte temporal (percentiles 70 y 85)...")
df = df.withColumn("ts_epoch", F.col("created_ts").cast("long"))

cortes = df.select(
    F.expr("percentile_approx(ts_epoch, 0.70, 10000)").alias("corte_70"),
    F.expr("percentile_approx(ts_epoch, 0.85, 10000)").alias("corte_85"),
).collect()[0]

corte_70 = cortes["corte_70"]
corte_85 = cortes["corte_85"]

fechas_corte = df.select(
    F.from_unixtime(F.lit(corte_70)).alias("fecha_corte_70"),
    F.from_unixtime(F.lit(corte_85)).alias("fecha_corte_85"),
).collect()[0]

print(f"   Corte 70% (train|val): {fechas_corte['fecha_corte_70']}")
print(f"   Corte 85% (val|test):  {fechas_corte['fecha_corte_85']}")

# 5. Aplicar los cortes
print("\n5. Generando splits temporales...")
train_df = df.filter(F.col("ts_epoch") <= corte_70)
val_df   = df.filter((F.col("ts_epoch") > corte_70) & (F.col("ts_epoch") <= corte_85))
test_df  = df.filter(F.col("ts_epoch") > corte_85)

cols_aux = ["ts_epoch"]
train_df = train_df.drop(*cols_aux)
val_df   = val_df.drop(*cols_aux)
test_df  = test_df.drop(*cols_aux)

n_train = train_df.count()
n_val   = val_df.count()
n_test  = test_df.count()
n_total = n_train + n_val + n_test

print(f"   Train : {n_train:>10,}  ({100*n_train/n_total:.1f}%)  [el 70% mas ANTIGUO]")
print(f"   Val   : {n_val:>10,}  ({100*n_val/n_total:.1f}%)  [el 15% intermedio]")
print(f"   Test  : {n_test:>10,}  ({100*n_test/n_total:.1f}%)  [el 15% mas RECIENTE]")

# 6. Verificaciones de integridad temporal
print("\n6. Verificacion de integridad temporal (NO debe haber solapamiento):")
rango_train = train_df.select(F.min("created_ts").alias("min"),
                              F.max("created_ts").alias("max")).collect()[0]
rango_val   = val_df.select(F.min("created_ts").alias("min"),
                            F.max("created_ts").alias("max")).collect()[0]
rango_test  = test_df.select(F.min("created_ts").alias("min"),
                             F.max("created_ts").alias("max")).collect()[0]

print(f"   Train: {rango_train['min']}  ->  {rango_train['max']}")
print(f"   Val:   {rango_val['min']}  ->  {rango_val['max']}")
print(f"   Test:  {rango_test['min']}  ->  {rango_test['max']}")

ok_tv = rango_train['max'] <= rango_val['min']
ok_vt = rango_val['max'] <= rango_test['min']
print(f"\n   Train termina antes que Val:  {ok_tv}")
print(f"   Val termina antes que Test:   {ok_vt}")
if ok_tv and ok_vt:
    print("   INTEGRIDAD TEMPORAL CONFIRMADA: sin solapamiento entre splits.")
else:
    print("   Hay un pequeno solapamiento en los bordes (empates de timestamp).")

# Distribucion de agencias por split
print("\n   Distribucion de agencias por split:")
ag_train = train_df.groupBy("Agency").count().withColumnRenamed("count", "train")
ag_val   = val_df.groupBy("Agency").count().withColumnRenamed("count", "val")
ag_test  = test_df.groupBy("Agency").count().withColumnRenamed("count", "test")
ag_train.join(ag_val, "Agency", "outer") \
        .join(ag_test, "Agency", "outer") \
        .fillna(0).orderBy("Agency").show(truncate=False)

# 7. Guardar splits temporales
print("\n7. Guardando splits temporales en S3...")
train_df.write.mode("overwrite").parquet(f"{PATH_SPLITS}/train/")
val_df.write.mode("overwrite").parquet(f"{PATH_SPLITS}/val/")
test_df.write.mode("overwrite").parquet(f"{PATH_SPLITS}/test/")
print(f"   Guardado en {PATH_SPLITS}/{{train,val,test}}/")

job.commit()
print("\nJob de split temporal por percentiles (Proyecto #2) finalizado.")