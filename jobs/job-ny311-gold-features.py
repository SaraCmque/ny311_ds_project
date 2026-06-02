import sys
import math
import json
import boto3
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F, Window
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType,
)
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder

# ═══════════════════════════════════════════════════════════════════
if "--JOB_NAME" in sys.argv:
    args = getResolvedOptions(sys.argv, ["JOB_NAME"])
else:
    args = {"JOB_NAME": "jupyter_interactive_job"}

sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

PATH_SPLITS = "s3://proyect-ny311/gold/splits_v2/ny311/"
PATH_GOLD   = "s3://proyect-ny311/gold_v2/ny311/"
PATH_ARTIFACTS = "s3://proyect-ny311/gold_v2/artifacts/"   # mapeos para inferencia
BUCKET = "proyect-ny311"

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 0 — DICCIONARIO DE NEGOCIO
# ═══════════════════════════════════════════════════════════════════
business_mapping = {
      "DOT":  (5.0, 83448.0),   "NYPD": (0.33, 64277.0),  
      "DSNY":  (5.0, 79301.0),  "DPR": (8.0, 68022.0),   
      "DOB": (40.0, 106907.0),  "DEP": (0.25, 75757.0),
      "HPD": (12.0, 252387.0),  "DOE": (36.0, 119316.0),  
      "DHS":  (0.04, 74717.0),  "DOHMH": (14.0, 74717.0), 
      "TLC":  (14.0, 74717.0),  "DCA": (28.0, 74717.0),
      "DOITT": (3.0, 74717.0)
}
lookup_rows   = [(a, float(s), float(p)) for a, (s, p) in business_mapping.items()]
lookup_schema = StructType([
    StructField("agency_key",        StringType(), False),
    StructField("sla_days",          DoubleType(), False),
    StructField("penalty_amount_usd", DoubleType(), False),
])
df_lookup = spark.createDataFrame(lookup_rows, schema=lookup_schema)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 1 — LEER SPLITS TEMPORALES
# ═══════════════════════════════════════════════════════════════════
print("1. Leyendo splits temporales...")
train_raw = spark.read.parquet(f"{PATH_SPLITS}/train/")
val_raw   = spark.read.parquet(f"{PATH_SPLITS}/val/")
test_raw  = spark.read.parquet(f"{PATH_SPLITS}/test/")
print(f"   Train: {train_raw.count():,} | Val: {val_raw.count():,} | Test: {test_raw.count():,}")

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 2 — RESOLUTION_TIME_DAYS
# ═══════════════════════════════════════════════════════════════════
print("\n2. Calculando resolution_time_days...")

def agregar_tiempos(df):
    return (
        df
        .withColumn("created_ts", F.to_timestamp("Created Date", "yyyy-MM-dd HH:mm:ss"))
        .withColumn("closed_ts",  F.to_timestamp("Closed Date",  "yyyy-MM-dd HH:mm:ss"))
        .withColumn(
            "resolution_time_days",
            (F.col("closed_ts").cast("long") - F.col("created_ts").cast("long")) / 86400.0
        )
        .withColumn("fecha_creacion", F.to_date("created_ts"))
    )

train_raw = agregar_tiempos(train_raw)
val_raw   = agregar_tiempos(val_raw)
test_raw  = agregar_tiempos(test_raw)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 3 — TARGET Y MULTA (convención: 1=incumple, 0=cumple)
# ═══════════════════════════════════════════════════════════════════
print("\n3. Aplicando target y multa...")

def aplicar_diccionario(df):
    return (
        df
        .join(df_lookup, df["Agency"] == df_lookup["agency_key"], "left")
        .drop("agency_key")
        .withColumn(
            "target",
            F.when(
                F.col("resolution_time_days").isNotNull()
                & F.col("sla_days").isNotNull()
                & (F.col("resolution_time_days") >= 0),
                F.when(F.col("resolution_time_days") > F.col("sla_days"), F.lit(1))
                 .otherwise(F.lit(0))
            ).cast(IntegerType())
        )
        .withColumn(
            "penalty_charged",
            F.when(F.col("target") == 0, F.lit(0.0))
             .when(F.col("target") == 1, F.col("penalty_amount_usd"))
             .cast(DoubleType())
        )
    )

train_raw = aplicar_diccionario(train_raw)
val_raw   = aplicar_diccionario(val_raw)
test_raw  = aplicar_diccionario(test_raw)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 5 — FEATURES TEMPORALES
#   MEJORA: eliminamos mes_sen/mes_cos (dataset solo 4 meses, ruido).
#           Mantenemos solo hora y día de semana cíclicos + trimestre.
# ═══════════════════════════════════════════════════════════════════
print("\n5. Features temporales...")

def agregar_features_temporales(df):
    return (
        df
        .withColumn("hora_creacion",  F.hour("created_ts"))
        .withColumn("dia_semana_raw", F.dayofweek("created_ts"))
        .withColumn("mes_raw",        F.month("created_ts"))
        .withColumn("hora_sen",       F.sin(2 * math.pi * F.col("hora_creacion") / 24))
        .withColumn("hora_cos",       F.cos(2 * math.pi * F.col("hora_creacion") / 24))
        .withColumn("dia_semana_sen", F.sin(2 * math.pi * F.col("dia_semana_raw") / 7))
        .withColumn("dia_semana_cos", F.cos(2 * math.pi * F.col("dia_semana_raw") / 7))
        .withColumn("es_fin_de_semana",
            F.when(F.col("dia_semana_raw").isin([1, 7]), 1).otherwise(0))
        .withColumn("turno",
            F.when((F.col("hora_creacion") >= 6)  & (F.col("hora_creacion") < 12), "manana")
             .when((F.col("hora_creacion") >= 12) & (F.col("hora_creacion") < 20), "tarde")
             .otherwise("noche"))
        .withColumn("trimestre", F.ceil(F.col("mes_raw") / 3).cast(IntegerType()))
        .drop("hora_creacion", "dia_semana_raw", "mes_raw")
    )

train_raw = agregar_features_temporales(train_raw)
val_raw   = agregar_features_temporales(val_raw)
test_raw  = agregar_features_temporales(test_raw)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 6 — INTERACCIÓN (solo borough_canal, las demás eran redundantes)
# ═══════════════════════════════════════════════════════════════════
print("6. Interacción categórica (solo borough_canal)...")

def agregar_interacciones(df):
    return df.withColumn("borough_canal",
                         F.concat_ws("_", F.col("Borough"), F.col("Open Data Channel Type")))

train_raw = agregar_interacciones(train_raw)
val_raw   = agregar_interacciones(val_raw)
test_raw  = agregar_interacciones(test_raw)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 7 — FEATURES GEOESPACIALES (calculadas SOLO en train)
#   Sin cambios respecto al P1: distancia a centroide + densidad ZIP 30d.
#   La densidad usa rangeBetween(-30,-1) → ya es correcta (solo mira atrás).
# ═══════════════════════════════════════════════════════════════════
print("7. Features geoespaciales...")

centroids_agency = (
    train_raw.groupBy("Agency", "Borough")
    .agg(F.mean("latitude").alias("centroid_lat_agency"),
         F.mean("longitude").alias("centroid_lon_agency"))
)

def distancia_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = F.radians(lat2 - lat1)
    dlon = F.radians(lon2 - lon1)
    a = (F.pow(F.sin(dlat / 2), 2)
         + F.cos(F.radians(lat1)) * F.cos(F.radians(lat2)) * F.pow(F.sin(dlon / 2), 2))
    return (2 * R * F.asin(F.sqrt(a))).cast(DoubleType())

def unir_distancia_agencia(df, centroids):
    return (df.join(centroids, ["Agency", "Borough"], "left")
            .withColumn("dist_km_agencia",
                distancia_haversine(F.col("latitude"), F.col("longitude"),
                                    F.col("centroid_lat_agency"), F.col("centroid_lon_agency")))
            .drop("centroid_lat_agency", "centroid_lon_agency"))

train_raw = unir_distancia_agencia(train_raw, centroids_agency)
val_raw   = unir_distancia_agencia(val_raw,   centroids_agency)
test_raw  = unir_distancia_agencia(test_raw,  centroids_agency)

# Densidad ZIP 30 días (rolling, solo mira hacia atrás)
train_con_epoch = train_raw.withColumn(
    "dias_epoch", F.datediff(F.col("fecha_creacion"), F.lit("2010-01-01")))
zip_daily = (train_con_epoch.groupBy("Incident Zip", "dias_epoch")
             .agg(F.count("*").alias("quejas_dia_zip")))
w_zip = (Window.partitionBy("Incident Zip").orderBy("dias_epoch").rangeBetween(-30, -1))
zip_density = (zip_daily
              .withColumn("densidad_zip_30d", F.sum("quejas_dia_zip").over(w_zip))
              .select("Incident Zip", "dias_epoch", "densidad_zip_30d"))

def unir_densidad_zip(df, zip_density_df):
    df_epoch = df.withColumn("dias_epoch", F.datediff(F.col("fecha_creacion"), F.lit("2010-01-01")))
    return df_epoch.join(zip_density_df, ["Incident Zip", "dias_epoch"], "left").drop("dias_epoch")

train_raw = unir_densidad_zip(train_raw, zip_density)
val_raw   = unir_densidad_zip(val_raw,   zip_density)
test_raw  = unir_densidad_zip(test_raw,  zip_density)

mediana_densidad = zip_density.groupBy("Incident Zip").agg(
    F.expr("percentile_approx(densidad_zip_30d, 0.5)").alias("med_densidad"))
global_mediana_densidad = zip_density.agg(
    F.expr("percentile_approx(densidad_zip_30d, 0.5)")).collect()[0][0]

def imputar_densidad(df, mediana_zip_df, global_med):
    return (df.join(mediana_zip_df, "Incident Zip", "left")
            .withColumn("densidad_zip_30d",
                F.coalesce(F.col("densidad_zip_30d"), F.col("med_densidad"), F.lit(global_med)))
            .drop("med_densidad"))

train_raw = imputar_densidad(train_raw, mediana_densidad, global_mediana_densidad)
val_raw   = imputar_densidad(val_raw,   mediana_densidad, global_mediana_densidad)
test_raw  = imputar_densidad(test_raw,  mediana_densidad, global_mediana_densidad)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 8 — VOLUMEN DIARIO GLOBAL
# ═══════════════════════════════════════════════════════════════════
print("8. Volumen diario global...")
quejas_por_dia = train_raw.groupBy("fecha_creacion").agg(F.count("*").alias("quejas_por_dia"))
mediana_quejas = quejas_por_dia.approxQuantile("quejas_por_dia", [0.5], 0.01)[0]

def unir_volumen_diario(df, qpd, mediana):
    return df.join(qpd, "fecha_creacion", "left").fillna({"quejas_por_dia": mediana})

train_raw = unir_volumen_diario(train_raw, quejas_por_dia, mediana_quejas)
val_raw   = unir_volumen_diario(val_raw,   quejas_por_dia, mediana_quejas)
test_raw  = unir_volumen_diario(test_raw,  quejas_por_dia, mediana_quejas)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 9 — AGREGACIONES HISTÓRICAS (calculadas SOLO en train)
# ═══════════════════════════════════════════════════════════════════
print("9. Agregaciones históricas...")
train_para_stats = train_raw.select(
    "Complaint Type", "Agency", "Borough", "Incident Zip", "resolution_time_days"
).filter(F.col("resolution_time_days").isNotNull() & (F.col("resolution_time_days") >= 0))

stats_tipo = train_para_stats.groupBy("Complaint Type").agg(
    F.mean("resolution_time_days").alias("avg_dias_complaint_type"),
    F.stddev("resolution_time_days").alias("std_dias_complaint_type"),
    F.expr("percentile_approx(resolution_time_days, 0.75)").alias("p75_dias_complaint_type"))
stats_agency  = train_para_stats.groupBy("Agency").agg(
    F.mean("resolution_time_days").alias("avg_dias_agency"))
stats_borough = train_para_stats.groupBy("Borough").agg(
    F.mean("resolution_time_days").alias("avg_dias_borough"))
stats_zip = train_para_stats.groupBy("Incident Zip").agg(
    F.mean("resolution_time_days").alias("avg_dias_zip"))

global_avg = train_para_stats.agg(F.mean("resolution_time_days")).collect()[0][0]
global_std = train_para_stats.agg(F.stddev("resolution_time_days")).collect()[0][0]
global_p75 = train_para_stats.agg(
    F.expr("percentile_approx(resolution_time_days, 0.75)")).collect()[0][0]

def unir_stats(df):
    return (df
        .join(stats_tipo,    "Complaint Type", "left")
        .join(stats_agency,  "Agency",         "left")
        .join(stats_borough, "Borough",        "left")
        .join(stats_zip,     "Incident Zip",   "left")
        .fillna({"avg_dias_complaint_type": global_avg, "std_dias_complaint_type": global_std,
                 "p75_dias_complaint_type": global_p75, "avg_dias_agency": global_avg,
                 "avg_dias_borough": global_avg, "avg_dias_zip": global_avg}))

train_raw = unir_stats(train_raw)
val_raw   = unir_stats(val_raw)
test_raw  = unir_stats(test_raw)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 9b — ★ NUEVAS FEATURES DE PRESIÓN Y SATURACIÓN ★
#
#   presion_sla        = avg_dias_complaint_type / sla_days
#       > 1 → ese tipo de queja históricamente tarda MÁS que su SLA
#   presion_sla_p75    = p75_dias_complaint_type / sla_days
#       versión robusta usando el percentil 75
#   saturacion_zip     = densidad_zip_30d / sla_days
#       presión local relativa a la exigencia del SLA
#   saturacion_diaria  = quejas_por_dia / sla_days
#       presión sistémica relativa al SLA
# ═══════════════════════════════════════════════════════════════════
print("9b. Features de presión y saturación (NUEVAS)...")

def agregar_presion(df):
    # +0.01 en denominador para evitar división por SLAs muy chicos (DHS=0.17)
    return (df
        .withColumn("presion_sla",
            F.col("avg_dias_complaint_type") / (F.col("sla_days") + F.lit(0.01)))
        .withColumn("presion_sla_p75",
            F.col("p75_dias_complaint_type") / (F.col("sla_days") + F.lit(0.01)))
        .withColumn("saturacion_zip",
            F.col("densidad_zip_30d") / (F.col("sla_days") + F.lit(0.01)))
        .withColumn("saturacion_diaria",
            F.col("quejas_por_dia") / (F.col("sla_days") + F.lit(0.01))))

train_raw = agregar_presion(train_raw)
val_raw   = agregar_presion(val_raw)
test_raw  = agregar_presion(test_raw)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 10 — CODIFICACIÓN CATEGÓRICA
#
#   BAJA CARDINALIDAD → StringIndexer (_idx) para árboles
#   ★ ALTA CARDINALIDAD → OUT-OF-FOLD TARGET ENCODING en train ★
#
#   El OOF encoding evita que cada fila de train vea su propio target.
#   Para val/test se usa el mean(target) de TODO train (sin leakage,
#   porque val/test no participaron en el cálculo).
# ═══════════════════════════════════════════════════════════════════
print("10. Codificación categórica...")

# --- 10a. StringIndexer (baja cardinalidad) ---
cols_baja_cardinalidad = ["Agency", "Borough", "Open Data Channel Type", "Location Type", "turno"]
indexers = [StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid="keep")
            for c in cols_baja_cardinalidad]
pipeline_encoding = Pipeline(stages=indexers)
encoder_model = pipeline_encoding.fit(train_raw)
train_raw = encoder_model.transform(train_raw)
val_raw   = encoder_model.transform(val_raw)
test_raw  = encoder_model.transform(test_raw)
print(f"   StringIndexer: {cols_baja_cardinalidad}")

# Guardar los mapeos del StringIndexer (categoría → índice) para inferencia
idx_mappings = {}
for stage, col in zip(encoder_model.stages, cols_baja_cardinalidad):
    labels = stage.labels  # lista ordenada por índice
    idx_mappings[f"{col}_idx"] = {label: float(i) for i, label in enumerate(labels)}

# --- 10b. OUT-OF-FOLD Target Encoding (alta cardinalidad) ---
cols_alta_cardinalidad = ["Complaint Type", "Incident Zip", "borough_canal"]
global_tasa = train_raw.agg(F.mean("target")).collect()[0][0]

# Asignar un fold aleatorio (5 folds) a cada fila de train
train_raw = train_raw.withColumn("fold", (F.rand(seed=42) * 5).cast(IntegerType()))

te_maps_full = {}  # mapas calculados con TODO train (para val/test e inferencia)

def aplicar_oof_target_encoding(train_df, col_name, global_mean):
    """
    Out-of-fold encoding: para cada fold, calcula el mean(target) usando
    los OTROS folds. Así ninguna fila ve su propio target.
    """
    # Suma y conteo por categoría y fold (para poder restar el propio fold)
    agg = (train_df.groupBy(col_name, "fold")
           .agg(F.sum("target").alias("s"), F.count("target").alias("c")))
    # Totales por categoría (todos los folds)
    tot = (train_df.groupBy(col_name)
           .agg(F.sum("target").alias("s_tot"), F.count("target").alias("c_tot")))
    # Para cada (categoria, fold): mean usando los OTROS folds = (s_tot - s)/(c_tot - c)
    oof = (agg.join(tot, col_name)
           .withColumn(f"{col_name}_te",
               F.when((F.col("c_tot") - F.col("c")) > 0,
                      (F.col("s_tot") - F.col("s")) / (F.col("c_tot") - F.col("c")))
                .otherwise(F.lit(global_mean)))
           .select(col_name, "fold", f"{col_name}_te"))
    return oof

# Aplicar OOF a train, y mapas completos a val/test
for col_name in cols_alta_cardinalidad:
    # Mapa OOF para train
    oof = aplicar_oof_target_encoding(train_raw, col_name, global_tasa)
    train_raw = train_raw.join(oof, [col_name, "fold"], "left") \
                         .fillna({f"{col_name}_te": global_tasa})
    # Mapa completo (todo train) para val/test e inferencia
    full_map = (train_raw.groupBy(col_name)
                .agg(F.mean("target").alias(f"{col_name}_te")))
    val_raw  = val_raw.join(full_map, col_name, "left").fillna({f"{col_name}_te": global_tasa})
    test_raw = test_raw.join(full_map, col_name, "left").fillna({f"{col_name}_te": global_tasa})
    # Guardar el mapa para inferencia
    te_maps_full[f"{col_name}_te"] = {
        str(row[col_name]): float(row[f"{col_name}_te"])
        for row in full_map.collect()
    }

train_raw = train_raw.drop("fold")
print(f"   OOF Target Encoding: {cols_alta_cardinalidad}")

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 11 — SELECCIÓN FINAL DE COLUMNAS
#   MEJORA: lista más limpia, sin redundancias, con las nuevas features.
# ═══════════════════════════════════════════════════════════════════
print("\n11. Seleccionando columnas finales...")

cols_originales_str = ["Complaint Type", "Agency", "Borough",
                       "Open Data Channel Type", "Location Type", "Incident Zip"]
cols_numericas_base = ["latitude", "longitude"]
cols_negocio        = ["sla_days", "penalty_amount_usd"]
cols_temporales     = ["hora_sen", "hora_cos", "dia_semana_sen", "dia_semana_cos",
                       "es_fin_de_semana", "trimestre", "quejas_por_dia"]
cols_historicas     = ["std_dias_complaint_type", "p75_dias_complaint_type",
                       "avg_dias_agency", "avg_dias_borough", "avg_dias_zip"]
cols_presion        = ["presion_sla", "presion_sla_p75",          # Nuevas
                       "saturacion_zip", "saturacion_diaria"]     # Nuevas
cols_geoespaciales  = ["dist_km_agencia", "densidad_zip_30d"]
cols_idx            = [f"{c}_idx" for c in cols_baja_cardinalidad]
cols_te             = [f"{c}_te"  for c in cols_alta_cardinalidad]
cols_target         = ["target", "penalty_charged"]

todas_cols = (cols_originales_str + cols_numericas_base + cols_negocio +
              cols_temporales + cols_historicas + cols_presion +
              cols_geoespaciales + cols_idx + cols_te + cols_target)

cols_obligatorias = (cols_numericas_base + cols_temporales + cols_historicas +
                     cols_presion + cols_geoespaciales + cols_target)

train_gold = train_raw.select(todas_cols).dropna(subset=cols_obligatorias)
val_gold   = val_raw.select(todas_cols).dropna(subset=cols_obligatorias)
test_gold  = test_raw.select(todas_cols).dropna(subset=cols_obligatorias)

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 12 — RESUMEN Y GUARDAR
# ═══════════════════════════════════════════════════════════════════
print("\n12. Resumen final:")
for nombre, df_out in [("Train", train_gold), ("Val", val_gold), ("Test", test_gold)]:
    total  = df_out.count()
    incump = df_out.filter(F.col("target") == 1).count()
    cumple = df_out.filter(F.col("target") == 0).count()
    multa  = df_out.agg(F.sum("penalty_charged")).collect()[0][0] or 0.0
    print(f"   {nombre:5}: {total:>9,} filas | "
          f"target=1 (incumplen): {incump:,} ({100*incump/total:.1f}%) | "
          f"target=0 (cumplen): {cumple:,} | multa total: ${multa:,.0f}")

print(f"\n   Total de features (sin target/multa/strings): "
      f"{len(todas_cols) - len(cols_originales_str) - len(cols_target)}")

print("\n13. Guardando Gold v2 en S3...")
train_gold.write.mode("overwrite").parquet(f"{PATH_GOLD}/train/")
val_gold.write.mode("overwrite").parquet(f"{PATH_GOLD}/val/")
test_gold.write.mode("overwrite").parquet(f"{PATH_GOLD}/test/")
print(f"   Guardado en {PATH_GOLD}/{{train,val,test}}/")

# ═══════════════════════════════════════════════════════════════════
# BLOQUE 14 — GUARDAR ARTEFACTOS PARA INFERENCIA
#   Guardamos en S3 un JSON con los mapeos exactos, para que la función
#   de inferencia NO tenga que aproximar nada.
# ═══════════════════════════════════════════════════════════════════
print("\n14. Guardando artefactos de inferencia...")

def df_to_dict(df, key_col, val_col):
    """Convierte un DataFrame a dict, filtrando claves o valores nulos."""
    return {
        str(r[key_col]): float(r[val_col])
        for r in df.collect()
        if r[key_col] is not None and r[val_col] is not None
    }

artifacts = {
    "business_mapping": business_mapping,
    "idx_mappings": idx_mappings,
    "te_maps_full": te_maps_full,
    "global_tasa": float(global_tasa) if global_tasa is not None else 0.2,
    "global_avg":  float(global_avg)  if global_avg  is not None else 0.0,
    "global_std":  float(global_std)  if global_std  is not None else 0.0,
    "global_p75":  float(global_p75)  if global_p75  is not None else 0.0,
    "global_densidad": float(global_mediana_densidad) if global_mediana_densidad is not None else 0.0,
    "mediana_quejas_por_dia": float(mediana_quejas) if mediana_quejas is not None else 0.0,
    "stats": {
        "avg_dias_complaint_type": df_to_dict(stats_tipo,    "Complaint Type", "avg_dias_complaint_type"),
        "std_dias_complaint_type": df_to_dict(stats_tipo,    "Complaint Type", "std_dias_complaint_type"),
        "p75_dias_complaint_type": df_to_dict(stats_tipo,    "Complaint Type", "p75_dias_complaint_type"),
        "avg_dias_agency":         df_to_dict(stats_agency,  "Agency",         "avg_dias_agency"),
        "avg_dias_borough":        df_to_dict(stats_borough, "Borough",        "avg_dias_borough"),
        "avg_dias_zip":            df_to_dict(stats_zip,     "Incident Zip",   "avg_dias_zip"),
    },
    "densidad_zip": df_to_dict(mediana_densidad, "Incident Zip", "med_densidad"),
    "dist_km_agencia": {
        f"{r['Agency']}_{r['Borough']}": float(r['dist_km_agencia'])
        for r in train_raw.groupBy("Agency", "Borough")
                          .agg(F.expr("percentile_approx(dist_km_agencia, 0.5)").alias("dist_km_agencia"))
                          .collect()
        if r['Agency'] is not None
        and r['Borough'] is not None
        and r['dist_km_agencia'] is not None     # ← este filtro arregla el error
    },
    "feature_order": [c for c in todas_cols
                      if c not in cols_originales_str + cols_target],
}

# Escribir JSON a S3
s3 = boto3.client("s3")
s3.put_object(
    Bucket=BUCKET,
    Key="gold_v2/artifacts/inference_artifacts.json",
    Body=json.dumps(artifacts, ensure_ascii=False, indent=2).encode("utf-8"),
)
print(f"   Artefactos guardados en {PATH_ARTIFACTS}inference_artifacts.json")

job.commit()
print("\nJob de features (Proyecto #2) finalizado.")
print("\nJob de features (Proyecto #2) finalizado.")
