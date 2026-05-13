import sys
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, TimestampType, DoubleType, IntegerType, LongType

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

df_silver = spark.read.parquet("s3://proyecto-ny311/silver/ny311/")
. Definición de grupos de interés
cols_geograficas = ["latitude", "longitude"]
cols_temporales = ["created date", "closed date"]
cols_categoricas = ["agency", "complaint type", "descriptor", "city", "borough", "status"]

stats_results = []

for col_name in df_silver.columns:
    c_lower = col_name.lower()
    dtype = df_silver.schema[col_name].dataType
    
    # Solo procesamos si la columna está en nuestras listas de interés
    if c_lower in (cols_geograficas + cols_temporales + cols_categoricas):
        
        # --- PASO A: CREAR DATAFRAME SIN NULOS PARA ESTA COLUMNA ---
        # Evitar que el valor más frecuente sea "nan"
        df_sin_nulos = df_silver.filter(F.col(col_name).isNotNull())
        
        min_v, max_v, mode_v, mean_v = "N/A", "N/A", "N/A", "N/A"

        # --- PASO B: CALCULAR LA MODA (Sobre el DF filtrado) ---
        # Agrupamos por la columna, contamos y tomamos el primero del orden descendente
        mode_row = df_sin_nulos.groupBy(col_name).count().orderBy(F.col("count").desc()).first()
        
        # Si mode_row no es None, extraemos el valor; si no, ponemos mensaje claro
        if mode_row:
            mode_v = str(mode_row[0])
        else:
            mode_v = "Sin datos válidos"

        # --- PASO C: CALCULAR MÉTRICAS ADICIONALES ---
        # Para coordenadas (Numéricas)
        if c_lower in cols_geograficas:
            res = df_sin_nulos.select(F.min(col_name), F.max(col_name), F.mean(col_name)).collect()[0]
            min_v = str(res[0]) if res[0] is not None else "N/A"
            max_v = str(res[1]) if res[1] is not None else "N/A"
            mean_v = str(round(res[2], 6)) if res[2] is not None else "N/A"
        
        # Para fechas (Temporales)
        elif isinstance(dtype, TimestampType) or c_lower in cols_temporales:
            res = df_sin_nulos.select(F.min(col_name), F.max(col_name)).collect()[0]
            min_v = str(res[0]) if res[0] is not None else "N/A"
            max_v = str(res[1]) if res[1] is not None else "N/A"

        # Guardamos los resultados de la columna actual
        stats_results.append((col_name, str(dtype), min_v, max_v, mode_v, mean_v))

# 2. Creación del DataFrame de resultados y guardado en S3
schema_eda = ["columna", "tipo", "minimo", "maximo", "moda", "media"]
df_eda_final = spark.createDataFrame(stats_results, schema=schema_eda)

# Guardamos en CSV para que Streamlit lo lea fácilmente
df_eda_final.coalesce(1).write.mode("overwrite").option("header", "true").csv("s3://proyecto-ny311/metadata/eda_silver/")

job.commit()