import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
import io

from eda_component import render_eda_section

# 1. Configuración de la página
st.set_page_config(page_title="NYC 311 Healthcheck", layout="wide")

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

@st.cache_data(ttl=3600)
def load_full_silver_data():
    s3 = get_s3_client()
    bucket = "proyecto-ny311"
    prefix = "silver/ny311/" 
    
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.parquet') or obj['Key'].endswith('.csv')]
        
        if not files:
            return None
            
        obj = s3.get_object(Bucket=bucket, Key=files[0])
        
        # Determinar el tipo de archivo y usar el reader apropiado
        if files[0].endswith('.parquet'):
            df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
        else:
            # Para archivos CSV
            df = pd.read_csv(io.BytesIO(obj['Body'].read()))
        return df
    except Exception as e:
        st.error(f"Error cargando datos Silver: {e}")
        return None

# --- CARGA INICIAL ---
df_full = load_full_silver_data()

# 3. Función para leer reportes
@st.cache_data(ttl=3600)
def load_report(prefix):
    s3_client = get_s3_client()
    bucket = "proyecto-ny311"
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = response.get('Contents', [])
        csv_files = [obj['Key'] for obj in objects if obj['Key'].endswith('.csv')]
        # Prefer actual part files from Spark output
        part_files = [key for key in csv_files if 'part-' in key]
        selected = part_files[0] if part_files else (csv_files[0] if csv_files else None)
        if selected is None:
            return None
        obj = s3_client.get_object(Bucket=bucket, Key=selected)
        return pd.read_csv(io.BytesIO(obj['Body'].read()))
    except Exception:
        return None

# --- UI PRINCIPAL ---
st.title("🛡️ Dashboard de Calidad y Estadísticas: NYC 311")

# ORGANIZACIÓN POR TABS
tab_calidad, tab_stats, tab_graficas = st.tabs([
    "✅ Control de Calidad", 
    "📊 Estadísticas (Tabla)", 
    "📈 Gráficas Dinámicas"
])
with tab_calidad:
    # =================================================================
    # SECCIÓN 1: BRONZE (TUS GRÁFICAS ORIGINALES)
    # =================================================================
    st.header("📊 Fase 1: Análisis Bronze (CSV Original)")
    df_bronze = load_report("metadata/healthcheck_report/")

    if df_bronze is not None:
        total_f = df_bronze["total_filas_dataset"].iloc[0]
        total_d = df_bronze["duplicados_dataset"].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Registros", f"{total_f:,}")
        col2.metric("Duplicados", f"{total_d:,}", delta_color="inverse")
        col3.metric("Calidad Inicial", f"{(1 - total_d/total_f)*100:.2f}%")

        st.divider()
        st.subheader("📋 Resumen de Columnas: Bronze")
        cols_to_show = ["columna", "tipo_dato", "nulos_n", "nulos_pct", "unicos_n", "outliers_n"]
        st.dataframe(df_bronze[cols_to_show], use_container_width=True)

        # Visualizaciones originales de Bronze
        c1, c2 = st.columns([0.6, 0.4])
        with c1:
            st.subheader("📉 % de Nulidad por Campo (Bronze)")
            df_sorted = df_bronze.sort_values("nulos_pct", ascending=True)
            h_dinamica = len(df_sorted) * 25
            fig = px.bar(df_sorted, x="nulos_pct", y="columna", orientation='h',
                         color="nulos_pct", color_continuous_scale="Reds", height=h_dinamica)
            fig.update_layout(margin=dict(l=150), yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("🚨 Distribución de Outliers")
            df_out = df_bronze[df_bronze["outliers_n"] > 0]
            if not df_out.empty:
                fig_out = px.pie(df_out, values="outliers_n", names="columna", hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_out, use_container_width=True)
            else:
                st.write("No se detectaron outliers.")

    # =================================================================
    # SECCIÓN 2: SILVER (TUS GRÁFICAS ORIGINALES)
    # =================================================================
    st.write("---")
    st.header("✨ Fase 2: Análisis Silver (Parquet Limpio)")
    df_silver = load_report("metadata/healthcheck_silver_parquet/")

    if df_silver is not None:
        total_s = df_silver["total_filas_dataset"].iloc[0]
        s1, s2, s3 = st.columns(3)
        s1.metric("Registros Únicos", f"{total_s:,}")
        s2.metric("Duplicados", "0", delta="Limpio", delta_color="normal")
        s3.metric("Reducción", f"{((total_f - total_s)/total_f)*100:.1f}%")

        st.divider()
        st.subheader("📋 Resumen de Columnas: Silver")
        st.dataframe(df_silver[["columna", "tipo_dato", "nulos_n", "nulos_pct", "unicos_n"]], use_container_width=True)

        # Visualizaciones originales de Silver
        sc1, sc2 = st.columns([0.6, 0.4])
        with sc1:
            st.subheader("📉 % de Nulidad por Campo (Silver)")
            df_s_sorted = df_silver.sort_values("nulos_pct", ascending=True)
            h_dinamica_s = len(df_s_sorted) * 25
            fig_s = px.bar(df_s_sorted, x="nulos_pct", y="columna", orientation='h',
                           color="nulos_pct", color_continuous_scale="Blues", height=h_dinamica_s)
            fig_s.update_layout(margin=dict(l=150), yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_s, use_container_width=True)
        with sc2:
            st.info("💡 **Observación de Ingeniería:** En esta etapa los duplicados son 0.")
    else:
        st.warning("⚠️ Reporte Silver no encontrado.")

with tab_stats:
    # Cargamos el reporte con las métricas corregidas
    df_eda_raw = load_report("metadata/eda_silver/")
    if df_eda_raw is not None:
        render_eda_section(df_eda_raw)
    else:
        st.warning("Reporte EDA no encontrado en S3.")

with tab_graficas:
    if df_full is not None:
        # Llamamos a la nueva función de gráficas con los 210k datos
        render_visual_charts(df_full)
    else:
        st.warning("No se pudieron cargar los datos para las gráficas.")