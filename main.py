import streamlit as st
from s3_utils import load_from_s3
from quality_component import render_quality_section
from eda_component import render_eda_section
from charts_component import render_dynamic_charts


st.set_page_config(page_title="NYC 311 Healthcheck", layout="wide")
st.title("NYC 311: Dashboard de Calidad de Datos y Estadísticas")

tab_calidad, tab_stats, tab_graficas = st.tabs([
    "✅ Control de Calidad", 
    "📊 Estadísticas (Tabla)", 
    "📈 Gráficas Dinámicas"
])

with tab_calidad:
    render_quality_section()

with tab_stats:
    df_eda = load_from_s3("metadata/eda_silver/")
    if df_eda is not None:
        render_eda_section(df_eda)
    else:
        st.warning("Reporte EDA no encontrado.")

with tab_graficas:
    render_dynamic_charts()