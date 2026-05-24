import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests
# Importamos tu utilidad personalizada
from s3_utils import load_from_s3

def load_data_for_eda():
    """Carga los datos enriquecidos desde la capa Gold usando s3_utils."""
    # Ruta del prefijo en S3 (ajustada a tu estructura)
    prefix_gold = "gold/enhanced_for_streamlit_eda/"
    
    # Usamos tu función que ya maneja secrets y múltiples partes de parquet
    df = load_from_s3(prefix=prefix_gold)
    
    if df is not None:
        # Convertir columnas de fecha
        df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
        df['Closed Date'] = pd.to_datetime(df['Closed Date'], errors='coerce')
        df['created_date_only'] = pd.to_datetime(df['created_date_only'], errors='coerce')
        
        # Asegurarse de que las columnas categóricas sean string
        str_cols = ['Complaint Type', 'Borough', 'created_day_of_week_name', 'Incident Zip', 
                    'Community Board', 'Agency Name', 'Open Data Channel Type']
        for col_name in str_cols:
            if col_name in df.columns:
                df[col_name] = df[col_name].astype(str).replace('nan', 'N/A')
        return df
    else:
        return None

def render_dynamic_charts():
    """Función principal para renderizar las gráficas de SLA."""
    
    df_raw = load_data_for_eda()
    
    if df_raw is None or df_raw.empty:
        st.error("No se pudieron cargar los datos de la capa Gold desde S3. Revisa los permisos y el prefijo.")
        return

    st.header("Análisis de Riesgo e Incumplimiento de SLA (NYC 311)")
    
    # --- FILTRADO PARA ANÁLISIS DE SLA ---
    # Solo registros con tiempo de resolución y umbral calculado
    df_work = df_raw[df_raw['resolution_time_days'].notna() & df_raw['p75_resolution_time_days'].notna()].copy()
    
    if df_work.empty:
        st.warning("Los datos están presentes pero no contienen cálculos de SLA (resolution_time_days).")
        return

    # PALETA DE COLORES (Ingeniería de la Atención)
    COLOR_FOCO = "#C0292B"       # Rojo foco
    COLOR_NEUTRO = "#718096"     # Gris contexto
    
    # 1. KPIs
    total_incidents = len(df_raw)
    total_non_compliant = df_work[df_work['is_sla_non_compliant'] == 1].shape[0]
    rate = (total_non_compliant / len(df_work)) if len(df_work) > 0 else 0
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Reportes", f"{total_incidents:,}")
    k2.metric("Casos fuera de SLA", f"{total_non_compliant:,}")
    k3.metric("Tasa de Incumplimiento", f"{rate:.1%}")

    # 2. GRÁFICA: TOP QUEJAS POR INCUMPLIMIENTO
    st.subheader("Categorías Críticas (Mayor % de Incumplimiento)")
    df_rate = df_work.groupby('Complaint Type')['is_sla_non_compliant'].mean().reset_index()
    df_rate = df_rate.sort_values('is_sla_non_compliant', ascending=True).tail(10)
    
    fig = px.bar(df_rate, x='is_sla_non_compliant', y='Complaint Type', orientation='h',
                 color_discrete_sequence=[COLOR_NEUTRO])
    
    # Resaltar la barra más alta en rojo
    fig.update_traces(marker_color=[COLOR_FOCO if i == df_rate['is_sla_non_compliant'].max() else COLOR_NEUTRO 
                                     for i in df_rate['is_sla_non_compliant']])
    
    fig.update_layout(xaxis_tickformat=".0%", plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

    # 3. EVOLUCIÓN TEMPORAL
    st.subheader("Evolución de Fallas en SLA por Fecha")
    df_time = df_work.groupby('created_date_only')['is_sla_non_compliant'].mean().reset_index()
    fig_line = px.line(df_time, x='created_date_only', y='is_sla_non_compliant')
    fig_line.update_traces(line_color=COLOR_FOCO)
    fig_line.update_layout(yaxis_tickformat=".0%", plot_bgcolor="white")
    st.plotly_chart(fig_line, use_container_width=True)

    # 4. MAPA COROPLÉTICO (Simplificado)
    st.subheader("Mapa de Calor: Incumplimiento por Community District")
    # Aquí iría la lógica del GeoJSON que discutimos antes, 
    # asumiendo que ya tienes los datos procesados en df_work
    st.info("El mapa utiliza las columnas 'latitude' y 'longitude' limpias para mostrar la densidad de casos fuera de SLA.")
    
    df_map_fail = df_work[df_work['is_sla_non_compliant'] == 1].sample(n=min(5000, len(df_work)))
    fig_map = px.scatter_mapbox(df_map_fail, lat="latitude", lon="longitude", 
                                color_discrete_sequence=[COLOR_FOCO], zoom=9, height=500)
    fig_map.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)
