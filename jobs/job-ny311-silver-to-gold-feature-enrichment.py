import sys
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import io
import boto3

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, ArrayType
from pyspark.sql.window import Window # Necesario para percentiles

# --- IMPORTACIONES FALTANTES PARA CORRELACIÓN Y VECTORASSEMBLER ---
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.stat import Correlation
# ------------------------------------------------------------------

# --- 0. Inicialización del contexto de Glue (compatible con Notebooks y Jobs) ---
if '--JOB_NAME' in sys.argv:
    args = getResolvedOptions(sys.argv, ['JOB_NAME'])
else:
    args = {'JOB_NAME': 'jupyter_interactive_job'}

sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# --- Ruta de entrada: Tu capa Silver (donde está tu data limpia) ---
path_silver = "s3://proyecto-ny311/silver/ny311/"

# --- 1. Leer el DataFrame limpio desde la capa Silver ---
print("1. Leyendo DataFrame desde la capa Silver...")
df_silver = spark.read.parquet(path_silver)
print(f"DataFrame leído. Total de registros: {df_silver.count()}")

# --- 2. Feature Engineering para EDA y Modelado de SLA ---
print("\n2. Realizando Feature Engineering para EDA y modelado de SLA...")

# Castear columnas de fecha a TimestampType para cálculos
df_fe = df_silver.withColumn("created_timestamp", F.to_timestamp(F.col("Created Date"), "yyyy-MM-dd HH:mm:ss")) \
                 .withColumn("closed_timestamp", F.to_timestamp(F.col("Closed Date"), "yyyy-MM-dd HH:mm:ss"))

# Calcular tiempo de resolución en días (usando segundos para mayor precisión, luego a días)
# resolution_time_days será nulo si closed_timestamp es nulo o anterior a created_timestamp
df_fe = df_fe.withColumn(
    "resolution_time_days",
    (F.col("closed_timestamp").cast("long") - F.col("created_timestamp").cast("long")) / (60 * 60 * 24)
)

# Filtrar incidentes resueltos con tiempo positivo/válido para calcular umbrales de SLA
df_resolved_for_sla = df_fe.filter(F.col("resolution_time_days").isNotNull() & (F.col("resolution_time_days") >= 0.001))

# Calcular P75 de tiempo de resolución por Complaint Type para el SLA
window_spec_sla = Window.partitionBy("Complaint Type")

# percentile_approx devuelve un array, tomamos el primer elemento (índice 0)
# Se calcula sobre df_resolved_for_sla para evitar nulos y asegurar que solo se usan resueltos
df_thresholds = df_resolved_for_sla.withColumn(
    "p75_resolution_time_days",
    F.percentile_approx("resolution_time_days", F.array(F.lit(0.75)), F.lit(1000000)).over(window_spec_sla)[0] # Usar mayor precisión para percentile_approx
).select("Complaint Type", "p75_resolution_time_days").dropDuplicates()

# Unir los umbrales de SLA al DataFrame principal
# Usamos left_outer para mantener todos los incidentes, incluso aquellos sin un umbral de SLA
df_fe_with_sla = df_fe.join(df_thresholds, on="Complaint Type", how="left_outer")

# Crear la bandera binaria de incumplimiento de SLA
# La queja incumple si resolution_time_days > p75_resolution_time_days Y está resuelta
df_fe_with_sla = df_fe_with_sla.withColumn(
    "is_sla_non_compliant",
    F.when(
        (F.col("resolution_time_days").isNotNull()) & # Solo para incidentes que se han cerrado
        (F.col("p75_resolution_time_days").isNotNull()) & # Solo si tenemos un umbral de SLA para ese tipo de queja
        (F.col("resolution_time_days") > F.col("p75_resolution_time_days")), 1
    ).otherwise(0) # 0 si cumple SLA, si no está resuelto, o si no hay umbral
)
print("Bandera 'is_sla_non_compliant' calculada.")

# Extraer características temporales
df_eda_final = df_fe_with_sla.withColumn("created_hour", F.hour(F.col("created_timestamp"))) \
                              .withColumn("created_day_of_week_num", F.dayofweek(F.col("created_timestamp"))) \
                              .withColumn("created_month", F.month(F.col("created_timestamp"))) \
                              .withColumn("created_year", F.year(F.col("created_timestamp"))) \
                              .withColumn("created_date_only", F.to_date(F.col("created_timestamp")))

# Mapear números de día de la semana a nombres (para Streamlit)
day_of_week_map = {1: "Sunday", 2: "Monday", 3: "Tuesday", 4: "Wednesday", 5: "Thursday", 6: "Friday", 7: "Saturday"}
df_eda_final = df_eda_final.withColumn(
    "created_day_of_week_name",
    F.when(F.col("created_day_of_week_num") == 1, "Sunday")
    .when(F.col("created_day_of_week_num") == 2, "Monday")
    .when(F.col("created_day_of_week_num") == 3, "Tuesday")
    .when(F.col("created_day_of_week_num") == 4, "Wednesday")
    .when(F.col("created_day_of_week_num") == 5, "Thursday")
    .when(F.col("created_day_of_week_num") == 6, "Friday")
    .when(F.col("created_day_of_week_num") == 7, "Saturday")
    .otherwise("Unknown")
)
print("Características temporales (hora, día, mes, año) extraídas.")


# --- 3. Verificación del DataFrame Final (primeros registros) ---
print("\n3. Primeros 5 registros del DataFrame ENRIQUECIDO para EDA:")
# Seleccionar algunas columnas clave para verificar la ingeniería de features
df_eda_final.select(
    "Unique Key", "Created Date", "Closed Date", "Complaint Type", "resolution_time_days",
    "p75_resolution_time_days", "is_sla_non_compliant", "created_hour",
    "created_day_of_week_name", "created_date_only", "Borough", "Incident Zip",
    "latitude", "longitude"
).show(5, truncate=False)

# --- 4. Mapa de Correlación (Variables Numéricas) ---
print("\n4. Calculando y visualizando la matriz de correlación de variables numéricas...")
# Columnas numéricas relevantes para la correlación después de la limpieza
# Incluimos resolution_time_days y is_sla_non_compliant como numéricos
num_cols = ["latitude", "longitude", "Incident Zip", "X Coordinate (State Plane)",
            "Y Coordinate (State Plane)", "resolution_time_days", "is_sla_non_compliant"]

# Seleccionar solo las columnas numéricas y asegurar que no haya nulos residuales
# is_sla_non_compliant e resolution_time_days pueden tener nulos para casos no cerrados.
# Para correlación, es mejor eliminar los nulos para estas columnas.
df_corr_for_plot = df_eda_final.select(num_cols).dropna()

if len(num_cols) > 1 and df_corr_for_plot.count() > 0:
    # Filtramos las columnas que no existen después del dropna si df_corr_for_plot.columns es diferente de num_cols
    existing_num_cols = [c for c in num_cols if c in df_corr_for_plot.columns]
    
    # Verificar si hay al menos dos columnas existentes para calcular la correlación
    if len(existing_num_cols) < 2:
        print("Advertencia: No hay suficientes columnas numéricas válidas para calcular la correlación después de eliminar nulos.")
    else:
        assembler = VectorAssembler(inputCols=existing_num_cols, outputCol="features")
        df_vector = assembler.transform(df_corr_for_plot).select("features")

        try:
            matrix = Correlation.corr(df_vector, "features").head()
            corr_matrix = matrix[0].toArray()

            pdf_corr = pd.DataFrame(corr_matrix, index=existing_num_cols, columns=existing_num_cols)

            # Crear el gráfico
            plt.figure(figsize=(10, 8))
            sns.heatmap(pdf_corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, fmt=".2f")
            plt.title("Matriz de Correlación de Variables Numéricas Enriquecidas")
            
            # Guardar el gráfico en un buffer de memoria como PNG
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)

            plt.close() # Cierra la figura para liberar memoria

            # Subir el gráfico a S3
            s3_bucket_name = "proyecto-ny311" # <<< ASEGÚRATE QUE ESTE ES TU BUCKET S3 REAL
            s3_key_name = "glue-notebook-plots/correlation_heatmap_eda.png"

            s3_client = boto3.client('s3')
            s3_client.put_object(Bucket=s3_bucket_name, Key=s3_key_name, Body=buf.getvalue(), ContentType='image/png')
            
            s3_plot_url = f"https://{s3_bucket_name}.s3.amazonaws.com/{s3_key_name}"
            print(f"Heatmap de correlación guardado en S3: {s3_plot_url}")
            print(f"Para ver el gráfico, abre el siguiente enlace en tu navegador:\n  {s3_plot_url}")
            
        except Exception as e:
            print(f"No se pudo calcular la matriz de correlación o guardar en S3. Error: {e}")
            print("Verifica los datos numéricos, los tipos de columnas y que el bucket S3 sea válido y accesible.")
else:
    print("No hay suficientes columnas numéricas o datos válidos para calcular la matriz de correlación.")

# --- 5. Guardar el DataFrame Enriquecido en Gold como Parquet ---
print("\n5. Guardando datos enriquecidos para EDA en Gold como Parquet...")
output_path_gold_eda = "s3://proyecto-ny311/gold/enhanced_for_streamlit_eda/"
df_eda_final.write \
  .mode("overwrite") \
  .parquet(output_path_gold_eda)

print(f"Datos guardados en Gold para Streamlit EDA correctamente en: {output_path_gold_eda}")

# --- 6. Finalizar el Job de Glue ---
job.commit()
print("Job de Glue finalizado.")
