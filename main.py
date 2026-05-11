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
    return boto3.client(
        's3',
        aws_access_key_id=st.secrets["aws"]["access_key"],
        aws_secret_access_key=st.secrets["aws"]["secret_key"],
        aws_session_token=st.secrets["aws"].get("session_token"),
        region_name=st.secrets["aws"]["region"]
    )

# 3. Función para leer reportes (Parametrizada para reusar estética)
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
        st.error(f"Error al conectar con S3 ({prefix}): {e}")
        return None

# --- UI PRINCIPAL ---
st.title("🛡️ Dashboard de Calidad: NYC 311")

# =================================================================
# SECCIÓN BRONZE (ORIGINAL)
# =================================================================
st.header("📊 Fase 1: Análisis Bronze (CSV Original)")
df_bronze = load_report("metadata/healthcheck_report/")

if df_bronze is not None:
    # MÉTRICAS ALTO NIVEL
    total_f = df_bronze["total_filas_dataset"].iloc[0]
    total_d = df_bronze["duplicados_dataset"].iloc[0]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Registros", f"{total_f:,}")
    m2.metric("Duplicados", f"{total_d:,}", delta_color="inverse")
    m3.metric("Calidad Inicial", f"{(1 - total_d/total_f)*100:.2f}%")

    st.divider()

    # VISUALIZACIONES BRONZE
    c1, c2 = st.columns([0.6, 0.4])

    with c1:
        st.subheader("📉 % de Nulidad por Campo (Bronze)")
        df_sorted = df_bronze.sort_values("nulos_pct", ascending=True)
        h_dinamica = len(df_sorted) * 25

        fig = px.bar(
            df_sorted, x="nulos_pct", y="columna", orientation='h',
            color="nulos_pct", color_continuous_scale="Reds",
            labels={"nulos_pct": "% Nulos", "columna": "Campo"},
            height=h_dinamica
        )
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
            st.write("No se detectaron valores atípicos.")

# =================================================================
# SECCIÓN SILVER (PARQUET SIN DUPLICADOS)
# =================================================================
st.write("---")
st.header("✨ Fase 2: Análisis Silver (Parquet Limpio)")
st.markdown("Resultados obtenidos tras aplicar `dropDuplicates` en AWS Glue.")

df_silver = load_report("metadata/healthcheck_silver_parquet/")

if df_silver is not None:
    # MÉTRICAS ALTO NIVEL SILVER
    total_s = df_silver["total_filas_dataset"].iloc[0]
    
    # En Silver ya no hay duplicados, ajustamos las métricas
    s1, s2, s3 = st.columns(3)
    s1.metric("Registros Únicos", f"{total_s:,}")
    s2.metric("Duplicados", "0", delta="Limpio", delta_color="normal")
    s3.metric("Ganancia de Eficiencia", f"{((total_f - total_s)/total_f)*100:.1f}% menos filas")

    st.divider()

    # VISUALIZACIONES SILVER (Misma estética que Bronze)
    sc1, sc2 = st.columns([0.6, 0.4])

    with sc1:
        st.subheader("📉 % de Nulidad por Campo (Silver)")
        df_s_sorted = df_silver.sort_values("nulos_pct", ascending=True)
        h_dinamica_s = len(df_s_sorted) * 25

        fig_s = px.bar(
            df_s_sorted, x="nulos_pct", y="columna", orientation='h',
            color="nulos_pct", color_continuous_scale="Blues", # Azul para diferenciar pero misma lógica
            labels={"nulos_pct": "% Nulos", "columna": "Campo"},
            height=h_dinamica_s
        )
        fig_s.update_layout(margin=dict(l=150), yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_s, use_container_width=True)

    with sc2:
        st.subheader("📋 Resumen de Columnas Silver")
        # Aquí mostramos el dataframe detallado para mantener la estética de dos paneles
        st.dataframe(
            df_silver[["columna", "tipo_dato", "nulos_pct", "unicos_n"]].sort_values("nulos_pct", ascending=False),
            use_container_width=True,
            height=400
        )
else:
    st.info("💡 Ejecuta el Job de Glue para generar el reporte de nulidad sobre los datos únicos en 'metadata/healthcheck_silver_parquet/'.")