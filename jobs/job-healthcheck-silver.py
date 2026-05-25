import sys
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

# Inicialización
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# 1. LEER LA TABLA EXISTENTE EN PARQUET
path_silver = "s3://proyecto-ny311/silver/ny311/"
df_silver = spark.read.parquet(path_silver)

# 2. CALCULAR MÉTRICAS PARA TODAS LAS COLUMNAS
total_filas = df_silver.count()
metrics_list = []

for col_name in df_silver.columns:
    # Contamos nulos, vacíos y el valor "Unspecified" (común en NYC 311)
    null_count = df_silver.filter(
        F.col(col_name).isNull() | 
        (F.col(col_name) == "") | 
        (F.col(col_name) == "Unspecified")
    ).count()
    
    unique_count = df_silver.select(col_name).distinct().count()
    
    metrics_list.append((
        col_name,
        str(df_silver.schema[col_name].dataType),
        null_count,
        round((null_count / total_filas) * 100, 2),
        unique_count,
        total_filas
    ))

# 3. CREAR DATAFRAME DE RESULTADOS
schema_metrics = ["columna", "tipo_dato", "nulos_n", "nulos_pct", "unicos_n", "total_filas_dataset"]
df_health_silver = spark.createDataFrame(metrics_list, schema=schema_metrics)

# 4. GUARDAR REPORTE (Metadata Layer para Silver)
output_path = "s3://proyecto-ny311/metadata/healthcheck_silver_parquet/"
df_health_silver.coalesce(1).write.mode("overwrite").option("header", "true").csv(output_path)

job.commit()