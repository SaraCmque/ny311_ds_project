import streamlit as st
# 1. Añadimos las importaciones de utilidades de datos y del nuevo componente
from s3_utils import load_from_s3 
from quality_component import render_quality_section
from charts_component import render_dynamic_charts
from model_component import render_model_section
from map_component import render_map_section 

st.set_page_config(page_title="NYC 311 Healthcheck", layout="wide")
st.title("NYC 311: Dashboard de Calidad de Datos y Estadísticas")

@st.cache_data
def get_gold_map_data():
    try:
        df_gold = load_from_s3("gold/visualizations/")
        if df_gold is not None and not df_gold.empty:
            return df_gold.dropna(subset=["latitude", "longitude"])
        return None
    except Exception as e:
        st.error(f"Error al conectar con la capa Gold en S3: {e}")
        return None

df_gold_map = get_gold_map_data()

tab_calidad, tab_modelo, tab_graficas = st.tabs([
    "✅ Control de Calidad",
    "🤖 Modelo Predictivo",
    "📊 Componente de Visualización",
])

with tab_calidad:
    render_quality_section()

with tab_modelo:
    render_model_section()

with tab_graficas:
    render_dynamic_charts()
    st.divider()
    if df_gold_map is not None:
        render_map_section(df_gold_map)
    else:
        st.warning("No se pudo estructurar el mapa porque los datos de la capa Gold están ausentes o vacíos.")