import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from io import BytesIO
from s3_utils import get_s3_client, load_from_s3 # Usamos tus utilidades

def display_correlation_heatmap():
    """Descarga y muestra la imagen de correlación guardada por Glue."""
    st.subheader("🔗 Matriz de Correlación (Variables Numéricas)")
    st.info("Este análisis identifica la relación estadística entre las coordenadas, el código postal y el incumplimiento de SLA.")
    
    bucket = "proyecto-ny311"
    key = "glue-notebook-plots/correlation_heatmap_eda.png"
    
    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=bucket, Key=key)
        img_bytes = response['Body'].read()
        st.image(img_bytes, caption="Correlación generada en el procesamiento Gold", use_container_width=True)
    except Exception as e:
        st.warning("Aún no se ha generado la imagen de correlación o no hay acceso al archivo.")

def render_dynamic_charts():
    prefix_gold = "gold/enhanced_for_streamlit_eda/"
    df_raw = load_from_s3(prefix=prefix_gold)
    
    if df_raw is None or df_raw.empty:
        st.error("No se pudieron cargar los datos.")
        return

    # --- INGENIERÍA DE LA ATENCIÓN: NUEVA LÓGICA DE GRÁFICA ---
    # Filtramos para tener datos con SLA
    df_work = df_raw[df_raw['p75_resolution_time_days'].notna()].copy()

    st.header("Análisis de Riesgo e Incumplimiento de SLA")
    
    # 1. MOSTRAR CORRELACIÓN (Primero o Segundo según importancia)
    display_correlation_heatmap()
    
    st.divider()

    # 2. GRÁFICA REFORMULADA: UMBRALES DE TIEMPO POR CATEGORÍA
    st.subheader("Lentitud por Categoría: ¿A los cuántos días se considera 'Falla'?")
    st.markdown("""
    Cada barra representa el **Percentil 75** de tiempo de resolución. 
    Este es el umbral que separa una gestión normal de una **crítica**.
    """)

    # Obtenemos el valor del P75 por categoría (es único por categoría)
    df_thresholds = df_work.groupby('Complaint Type')['p75_resolution_time_days'].first().reset_index()
    df_thresholds = df_thresholds.sort_values('p75_resolution_time_days', ascending=True).tail(12)

    COLOR_FOCO = "#C0292B"
    COLOR_NEUTRO = "#718096"

    # Calculamos la media de los umbrales para resaltar las que son "excesivamente lentas"
    promedio_umbrales = df_thresholds['p75_resolution_time_days'].mean()

    fig = px.bar(
        df_thresholds, 
        x='p75_resolution_time_days', 
        y='Complaint Type', 
        orientation='h',
        labels={'p75_resolution_time_days': 'Días para entrar en Incumplimiento (P75)'}
    )

    # Resaltado selectivo: Rojo si el umbral de la categoría supera el promedio de la ciudad
    colores = [COLOR_FOCO if v > promedio_umbrales else COLOR_NEUTRO for v in df_thresholds['p75_resolution_time_days']]
    fig.update_traces(marker_color=colores, opacity=0.85)

    fig.add_vline(x=promedio_umbrales, line_dash="dash", line_color="black", 
                  annotation_text=f"Promedio Ciudad: {promedio_umbrales:.1f} días")

    fig.update_layout(plot_bgcolor="white", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # 3. MAPA DE FALLAS (Solo puntos críticos)
    st.subheader("📍 Geografía del Incumplimiento")
    st.write("Visualización de las coordenadas exactas de casos que ya superaron su SLA.")
    df_fail = df_work[df_work['is_sla_non_compliant'] == 1].sample(n=min(3000, len(df_work)))
    
    fig_map = px.scatter_mapbox(
        df_fail, lat="latitude", lon="longitude", 
        color_discrete_sequence=[COLOR_FOCO], 
        zoom=10, height=600,
        hover_name="Complaint Type",
        mapbox_style="carto-positron"
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)
