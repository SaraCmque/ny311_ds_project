import streamlit as st
from quality_component import render_quality_section
from charts_component import render_dynamic_charts
from model_component import render_model_section


st.set_page_config(page_title="NYC 311 Healthcheck", layout="wide")
st.title("NYC 311: Dashboard de Calidad de Datos y Estadísticas")

tab_calidad, tab_graficas, tab_modelo = st.tabs([
    "✅ Control de Calidad",
    "📈 Gráficas Dinámicas",
    "🤖 Modelo Predictivo",
])

with tab_calidad:
    render_quality_section()

with tab_graficas:
    render_dynamic_charts()

with tab_modelo:
    render_model_section()
