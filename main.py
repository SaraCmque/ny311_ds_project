import streamlit as st
from quality_component import render_quality_section
from charts_component import render_dynamic_charts


st.set_page_config(page_title="NYC 311 Healthcheck", layout="wide")
st.title("NYC 311: Dashboard de Calidad de Datos y Estadísticas")

tab_calidad, tab_graficas = st.tabs([
    "✅ Control de Calidad",
    "📈 Gráficas Dinámicas"
])

with tab_calidad:
    render_quality_section()

with tab_graficas:
    render_dynamic_charts()
