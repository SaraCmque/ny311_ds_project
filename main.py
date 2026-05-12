import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
import io

# IMPORTACIÓN DEL MÓDULO DESCENTRALIZADO
from eda_component import render_eda_section

# 1. Configuración de la página
st.set_page_config(page_title="NYC 311 Intelligence Platform", layout="wide")

# 2. Gestión de Conexión Segura con Boto3
@st.cache_resource
def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=st.secrets["aws"]["access_key"],
        aws_secret_access_key=st.secrets["aws"]["secret_key"],
        aws_session_token=st.secrets["aws"].get("session_token"),
        region_name=st.secrets["aws"]["region"]
    )

# 3. Función para leer reportes
@st.cache_data(ttl=3600)
def load_report(prefix):
    s3 = get_s3_client()
    bucket = "proyecto-ny311"
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = response.get('Contents', [])
        csv_files = [obj['Key'] for obj in objects if obj['Key'].endswith('.csv')]
        if not csv_files:
            return None
        obj = s3.get_object(Bucket=bucket, Key=csv_files[0])
        return pd.read_csv(io.BytesIO(obj['Body'].read()))
    except Exception as e:
        return None

# --- UI PRINCIPAL ---
st.title("🛡️ Dashboard Central NYC 311")

# Organización por Pestañas Principales para evitar código espagueti
tab_health, tab_stats = st.tabs(["✅ Control de Calidad", "📊 Estadísticas EDA"])

with tab_health:
    # =================================================================
    # SECCIÓN: CALIDAD (BRONZE & SILVER HEALTHCHECK)
    # =================================================================
    st.header("Análisis de Salud de Datos")
    
    # --- Lógica Bronze ---
    df_bronze = load_report("metadata/healthcheck_report/")
    if df_bronze is not None:
        total_f = df_bronze["total_filas_dataset"].iloc[0]
        total_d = df_bronze["duplicados_dataset"].iloc[0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registros (Bronze)", f"{total_f:,}")
        c2.metric("Duplicados", f"{total_d:,}", delta_color="inverse")
        c3.metric("Calidad Inicial", f"{(1 - total_d/total_f)*100:.2f}%")

        st.subheader("📋 Resumen de Columnas: Bronze")
        st.dataframe(df_bronze[["columna", "tipo_dato", "nulos_n", "nulos_pct", "unicos_n", "outliers_n"]], use_container_width=True)

    st.divider()

    # --- Lógica Silver Quality ---
    st.header("✨ Fase 2: Análisis Silver (Limpio)")
    df_silver_qc = load_report("metadata/healthcheck_silver_parquet/")
    if df_silver_qc is not None:
        total_s = df_silver_qc["total_filas_dataset"].iloc[0]
        s1, s2, s3 = st.columns(3)
        s1.metric("Registros Únicos (Silver)", f"{total_s:,}")
        s2.metric("Duplicados", "0", delta="Limpio", delta_color="normal")
        s3.metric("Reducción de Data", f"{((total_f - total_s)/total_f)*100:.1f}%")
        
        st.dataframe(df_silver_qc[["columna", "tipo_dato", "nulos_n", "nulos_pct", "unicos_n"]], use_container_width=True)
    else:
        st.warning("Reporte Silver no encontrado.")

with tab_stats:
    # =================================================================
    # SECCIÓN: EDA (MÓDULO DESCENTRALIZADO)
    # =================================================================
    # Cargamos el reporte específico de estadísticas (el que tiene moda, media, etc.)
    df_eda_data = load_report("metadata/eda_silver/")
    
    if df_eda_data is not None:
        # LLAMADA AL MÓDULO EXTERNO
        render_eda_section(df_eda_data)
    else:
        st.error("🚨 Reporte de estadísticas (EDA) no encontrado en S3.")
        st.info("Asegúrate de ejecutar el Job de Glue que genera 'metadata/eda_silver/'.")