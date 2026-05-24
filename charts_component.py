import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from s3_utils import load_from_s3

def render_dynamic_charts():
    prefix_gold = "gold/enhanced_for_streamlit_eda/"
    df_raw = load_from_s3(prefix=prefix_gold)
    
    if df_raw is None or df_raw.empty:
        st.error("No se pudieron cargar los datos de la capa Gold.")
        return

    # Colores estratégicos
    COLOR_FOCO = "#C0292B"   # Rojo: Incumplimiento / Riesgo
    COLOR_NEUTRO = "#718096" # Gris: Contexto
    
    st.header("🎯 Storytelling de Riesgo: Predicción de Incumplimiento de SLA")
    st.markdown("""
    **Objetivo de Negocio:** Identificar patrones que incrementan la probabilidad de que una queja supere el tiempo de respuesta esperado (P75). 
    *No todas las quejas son iguales: la ineficiencia tiene horarios, zonas y categorías específicas.*
    """)

    # 1. KPIs DE IMPACTO
    df_work = df_raw[df_raw['p75_resolution_time_days'].notna()].copy()
    total_casos = len(df_work)
    casos_fuera_sla = df_work[df_work['is_sla_non_compliant'] == 1].shape[0]
    tasa_global = (casos_fuera_sla / total_casos) if total_casos > 0 else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Incidentes Analizados", f"{total_casos:,}")
    k2.metric("Casos en Riesgo (Fuera de SLA)", f"{casos_fuera_sla:,}")
    k3.metric("Tasa de Fallo Crítico", f"{tasa_global:.1%}")

    st.divider()

    # 2. DISTRIBUCIÓN DE UMBRALES (EL PORQUÉ DEL MODELO)
    st.subheader("1. La brecha de tiempos: ¿Cuándo falla el sistema?")
    st.info("Justificación del Target: Cada categoría tiene su propio 'reloj'. El modelo aprenderá a predecir quién saltará estas vallas.")
    
    df_thresholds = df_work.groupby('Complaint Type')['p75_resolution_time_days'].first().reset_index()
    df_thresholds = df_thresholds.sort_values('p75_resolution_time_days', ascending=True).tail(10)
    
    fig_thr = px.bar(df_thresholds, x='p75_resolution_time_days', y='Complaint Type', orientation='h',
                     title="Umbrales Críticos (Días para considerar falla)")
    
    # Resaltar solo la más lenta para forzar la atención
    colores_thr = [COLOR_FOCO if x == df_thresholds['p75_resolution_time_days'].max() else COLOR_NEUTRO for x in df_thresholds['p75_resolution_time_days']]
    fig_thr.update_traces(marker_color=colores_thr, opacity=0.8)
    fig_thr.update_layout(plot_bgcolor="white", xaxis_title="Días (P75)")
    st.plotly_chart(fig_thr, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        # 3. RIESGO POR BOROUGH (Distribución Espacial)
        st.subheader("2. Riesgo por Distrito")
        df_boro_risk = df_work.groupby('Borough')['is_sla_non_compliant'].mean().reset_index()
        df_boro_risk = df_boro_risk.sort_values('is_sla_non_compliant', ascending=True)
        
        # Resaltamos el borough con mayor tasa de incumplimiento
        colores_boro = [COLOR_FOCO if r == df_boro_risk['is_sla_non_compliant'].max() else COLOR_NEUTRO for r in df_boro_risk['is_sla_non_compliant']]
        
        fig_boro = px.bar(df_boro_risk, x='is_sla_non_compliant', y='Borough', orientation='h',
                          title="Tasa de Incumplimiento por Borough")
        fig_boro.update_traces(marker_color=colores_boro)
        fig_boro.update_layout(plot_bgcolor="white", xaxis_tickformat=".0%")
        st.plotly_chart(fig_boro, use_container_width=True)

    with col_right:
        # 4. RIESGO POR HORA (Distribución Temporal)
        st.subheader("3. El factor horario")
        df_hour_risk = df_work.groupby('created_hour')['is_sla_non_compliant'].mean().reset_index()
        
        fig_hour = px.line(df_hour_risk, x='created_hour', y='is_sla_non_compliant',
                           title="Probabilidad de Incumplimiento según Hora de Creación")
        fig_hour.update_traces(line_color=COLOR_FOCO, line_width=3)
        fig_hour.update_layout(plot_bgcolor="white", yaxis_tickformat=".0%", yaxis_range=[0, df_hour_risk['is_sla_non_compliant'].max()*1.2])
        
        # Anotación para el punto más alto
        max_h_risk = df_hour_risk.loc[df_hour_risk['is_sla_non_compliant'].idxmax()]
        fig_hour.add_annotation(x=max_h_risk['created_hour'], y=max_h_risk['is_sla_non_compliant'],
                                text="Pico de riesgo", showarrow=True, arrowhead=1, font=dict(color=COLOR_FOCO))
        
        st.plotly_chart(fig_hour, use_container_width=True)

    st.divider()

    # 5. MAPA DE CALOR: FOCOS CRÍTICOS
    st.subheader("4. Mapa de Focos Geográficos de Incumplimiento")
    st.write("Cada punto representa una queja que **incumplió** su SLA. La densidad en ciertas zonas indica problemas estructurales de respuesta.")
    
    # Filtrar solo fallas para reducir ruido
    df_fail = df_work[df_work['is_sla_non_compliant'] == 1]
    # Muestra representativa para no saturar el navegador
    df_map_fail = df_fail.sample(n=min(5000, len(df_fail)))

    fig_map = px.scatter_mapbox(
        df_map_fail, 
        lat="latitude", 
        lon="longitude", 
        color_discrete_sequence=[COLOR_FOCO], 
        zoom=10, 
        height=600,
        hover_name="Complaint Type",
        mapbox_style="carto-positron",
        opacity=0.4 # Opacidad baja para ver dónde se acumulan más puntos (contraste figura-fondo)
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    st.success("✅ **Insight para Modelado:** El modelo de Machine Learning debería priorizar variables de 'Hora' y 'Borough', dado que presentan variaciones significativas en la tasa de fallo.")
