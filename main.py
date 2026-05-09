import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
import io

# 1. Configuración de la página
st.set_page_config(page_title="NYC 311 Healthcheck", layout="wide")

# 2. Gestión de Conexión Segura con Boto3
@st.cache_resource
def get_s3_client():
    """
    Crea el cliente de S3 usando los secretos de Streamlit.
    Asegúrate de tener configurado .streamlit/secrets.toml
    """
    return boto3.client(
        's3',
        aws_access_key_id=st.secrets["aws"]["access_key"],
        aws_secret_access_key=st.secrets["aws"]["secret_key"],
        aws_session_token=st.secrets["aws"].get("session_token"),
        region_name=st.secrets["aws"]["region"]
    )

# 3. Función para leer el reporte de Glue
@st.cache_data(ttl=3600) # El caché expira cada hora
def load_healthcheck_data():
    s3 = get_s3_client()
    bucket = "proyecto-ny311"
    prefix = "metadata/healthcheck_report/"
    
    try:
        # Listar archivos para encontrar el CSV (Glue genera nombres dinámicos)
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = response.get('Contents', [])
        
        # Filtrar solo el archivo .csv
        csv_files = [obj['Key'] for obj in objects if obj['Key'].endswith('.csv')]
        
        if not csv_files:
            st.error("No se encontró el archivo CSV en la ruta especificada.")
            return None
        
        # Leer el contenido del archivo directamente a memoria
        obj = s3.get_object(Bucket=bucket, Key=csv_files[0])
        df = pd.read_csv(io.BytesIO(obj['Body'].read()))
        return df

    except Exception as e:
        st.error(f"Error al conectar con S3: {e}")
        return None

# --- UI PRINCIPAL ---
st.title("🛡️ Dashboard de Calidad: NYC 311")
st.markdown("### Análisis de Big Data (25M+ Registros) procesados con AWS Glue")

df_metrics = load_healthcheck_data()

if df_metrics is not None:
    # --- MÉTRICAS DE ALTO NIVEL ---
    # Extraemos los valores globales (asumiendo que están en la primera fila)
    total_filas = df_metrics["total_filas_dataset"].iloc[0]
    total_dups = df_metrics["duplicados_dataset"].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Registros", f"{total_filas:,}")
    col2.metric("Duplicados", f"{total_dups:,}", delta_color="inverse")
    col3.metric("Calidad de Datos", f"{(1 - total_dups/total_filas)*100:.2f}%")

    st.divider()

    # --- TABLA DETALLADA ---
    st.subheader("📋 Estado de Columnas")
    # Columnas a mostrar en la tabla
    cols_to_show = ["columna", "tipo_dato", "nulos_n", "nulos_pct", "unicos_n", "outliers_n"]
    st.dataframe(df_metrics[cols_to_show], use_container_width=True)

    # --- VISUALIZACIONES ---
    c1, c2 = st.columns([0.6, 0.4]) # Ajustamos el ancho para darle más espacio al gráfico de barras

    with c1:
        st.subheader("📉 % de Nulidad por Campo")
        
        # Ordenamos los datos
        df_nulos_sorted = df_metrics.sort_values("nulos_pct", ascending=True)
        
        # Calculamos una altura dinámica: 25 píxeles por cada columna 
        # para asegurar que todas sean legibles.
        altura_dinamica = len(df_nulos_sorted) * 25

        fig_nulos = px.bar(
            df_nulos_sorted,
            x="nulos_pct", 
            y="columna",
            orientation='h',
            color="nulos_pct",
            color_continuous_scale="Reds",
            labels={"nulos_pct": "% Nulos", "columna": "Campo"},
            height=altura_dinamica # <--- Aplicamos la altura aquí
        )
        
        # Ajustes estéticos para que no se corten los nombres largos
        fig_nulos.update_layout(
            margin=dict(l=150), # Margen izquierdo extra para nombres de columnas
            yaxis={'categoryorder':'total ascending'}
        )
        
        st.plotly_chart(fig_nulos, use_container_width=True)

    with c2:
        st.subheader("🚨 Distribución de Outliers")
        df_out = df_metrics[df_metrics["outliers_n"] > 0]
        if not df_out.empty:
            fig_out = px.pie(
                df_out, 
                values="outliers_n", 
                names="columna",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_out, use_container_width=True)
        else:
            st.write("No se detectaron valores atípicos significativos.")

else:
    st.info("💡 Tip: Verifica que tus secretos en `.streamlit/secrets.toml` coincidan con tus credenciales de IAM.")