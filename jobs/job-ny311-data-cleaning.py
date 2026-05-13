import sys
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.functions import to_timestamp, datediff, col
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType

# Inicializar contexto
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

path_bronze = "s3://proyecto-ny311/bronze/311-service-requests-from-2010-to-present.csv"

# 1. Leer CSV desde Bronze
df = spark.read.csv(path_bronze, header=True, inferSchema=True)

df_clean = df.dropDuplicates(["Unique Key"])

cols_to_drop = [
    "Due Date", "Bridge Highway Name", "Vehicle Type", 
    "Taxi Company Borough", "Road Ramp", "Bridge Highway Segment", 
    "Bridge Highway Direction", "Park Facility Name", 
    "Taxi Pick Up Location", "Facility Type", "Location", "Zip Codes",
    "Community Districts", "Borough Boundaries"
]
df_drop = df_clean.drop(*cols_to_drop)

# 2. Imputación de campos de Texto (Categorías)
text_impute_map = {
    "Descriptor": "NOT PROVIDED",
    "Location Type": "UNKNOWN",
    "Incident Address": "UNKNOWN",
    "Street Name": "UNKNOWN",
    "City": "UNSPECIFIED",
    "Borough": "UNSPECIFIED",
    "Park Borough": "UNSPECIFIED"
}

df_imputed = df_drop.na.fill(text_impute_map)

# 3. Imputación de campos Numéricos
df_imputed = df_imputed.na.fill({"Incident Zip": 0})

df_imputed = df_imputed.withColumn("latitude", F.col("latitude").cast(DoubleType()))
df_imputed = df_imputed.withColumn("longitude", F.col("longitude").cast(DoubleType()))

# 4. Guardar en Silver como Parquet
df_imputed.write \
  .mode("overwrite") \
  .parquet("s3://proyecto-ny311/silver/ny311/")

print("Datos guardados en Silver correctamente")

job.commit()