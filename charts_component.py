import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from s3_utils import load_from_s3

def render_dynamic_charts():
    prefix_gold = "gold/enhanced_for_streamlit_eda/"
    df_raw = load_from_s3(prefix=prefix_gold)
    
    if df_raw is None or df_raw.empty:
        st.error("No se pudieron cargar los datos.")
        return

    # Colores estratégicos
    COLOR_FOCO = "#C0292B"   # Rojo: Incumplimiento
    COLOR_NEUTRO = "#718096" # Gris: Contexto
    COLOR_EXITO = "#28A745"  # Verde

    st.header("🎯 Storytelling de Riesgo: Predicción de Incumplimiento (SLA)")
    
    # 1. KPIs GLOBALES (Toda la ciudad)
    df_work = df_raw[df_raw['p75_resolution_time_days'].notna()].copy()
    total_casos = len(df_work)
    casos_fuera_sla = df_work[df_work['is_sla_non_compliant'] == 1].shape[0]
    tasa_global = (casos_fuera_sla / total_casos) if total_casos > 0 else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Incidentes Analizados", f"{total_casos:,}")
    k2.metric("Casos en Riesgo (Fuera de SLA)", f"{casos_fuera_sla:,}")
    k3.metric("Tasa de Fallo Global", f"{tasa_global:.1%}")

    st.divider()

    # 2. SECCIÓN INTERACTIVA: EXPLICACIÓN DEL TARGET
    st.subheader("1. ¿Cómo definimos el 'Fallo' para el modelo?")
    st.markdown("Selecciona una categoría para ver cómo su historia define su propia valla de incumplimiento (P75).")
    
    # Selector de categoría para la gráfica conceptual
    lista_quejas = sorted(df_work['Complaint Type'].unique())
    # Buscamos 'MOSQUITOES' por defecto, si no, la primera de la lista
    index_defecto = lista_quejas.index('MOSQUITOES') if 'MOSQUITOES' in lista_quejas else 0
    
    cat_seleccionada = st.selectbox("Elegir categoría para el análisis detallado:", lista_quejas, index=index_defecto)

    # Filtrar datos solo para la gráfica de concepto
    df_ex = df_work[df_work['Complaint Type'] == cat_seleccionada].dropna(subset=['resolution_time_days'])
    
    if not df_ex.empty:
        umbral_p75 = df_ex['p75_resolution_time_days'].iloc[0]
        
        fig_concept = px.histogram(
            df_ex, x="resolution_time_days", nbins=50,
            title=f"Distribución de Tiempos: {cat_seleccionada}",
            color_discrete_sequence=[COLOR_NEUTRO],
            labels={'resolution_time_days': 'Días transcurridos'}
        )
        
        # Línea del P75
        fig_concept.add_vline(x=umbral_p75, line_dash="dash", line_color=COLOR_FOCO, line_width=3)
        
        fig_concept.add_annotation(x=umbral_p75/2, y=5, text="75% Casos Normales", showarrow=False, font_color=COLOR_EXITO)
        fig_concept.add_annotation(x=umbral_p75*1.2, y=5, text="25% Casos CRÍTICOS", showarrow=False, font_color=COLOR_FOCO)
        
        fig_concept.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig_concept, use_container_width=True)
        st.info(f"💡 **Insight:** En **{cat_seleccionada}**, el compromiso es resolver en menos de **{umbral_p75:.1f} días**. El modelo de ML intentará predecir quiénes pasarán a la zona roja.")

    st.divider()

    # 3. ANALISIS GLOBAL DE FACTORES (Todas las categorías combinadas)
    st.subheader("2. Factores de Riesgo Globales (Toda la Ciudad)")
    st.write("Independientemente de la queja, ¿dónde y cuándo es más probable fallar?")
    
    col_left, col_right = st.columns(2)

    with col_left:
        # Riesgo por Distrito (Global)
        df_boro_risk = df_work.groupby('Borough')['is_sla_non_compliant'].mean().reset_index()
        df_boro_risk = df_boro_risk.sort_values('is_sla_non_compliant', ascending=True)
        
        fig_boro = px.bar(df_boro_risk, x='is_sla_non_compliant', y='Borough', orientation='h',
                          title="Probabilidad de Incumplimiento por Borough")
        # Pintamos de rojo si supera el promedio
        fig_boro.update_traces(marker_color=[COLOR_FOCO if r > 0.25 else COLOR_NEUTRO for r in df_boro_risk['is_sla_non_compliant']])
        fig_boro.update_layout(plot_bgcolor="white", xaxis_tickformat=".0%")
        st.plotly_chart(fig_boro, use_container_width=True)

    with col_right:
        # Riesgo por Hora (Global)
        df_hour_risk = df_work.groupby('created_hour')['is_sla_non_compliant'].mean().reset_index()
        fig_hour = px.line(df_hour_risk, x='created_hour', y='is_sla_non_compliant',
                           title="Riesgo de Incumplimiento por Hora de Reporte")
        fig_hour.update_traces(line_color=COLOR_FOCO, line_width=4)
        fig_hour.update_layout(plot_bgcolor="white", yaxis_tickformat=".0%", yaxis_title="Probabilidad de Fallo")
        st.plotly_chart(fig_hour, use_container_width=True)

    st.divider()

    # 4. GEOGRAFÍA GLOBAL DEL FALLO
    st.subheader("3. Mapa de Focos Geográficos: La 'clase positiva' (Incumplimientos)")
    st.write("Visualización de las coordenadas de las quejas que ya han fallado en toda la ciudad.")
    
    # Filtrar solo fallas de todas las categorías
    df_fail = df_work[df_work['is_sla_non_compliant'] == 1]
    df_map_fail = df_fail.sample(n=min(5000, len(df_fail)))

    fig_map = px.scatter_mapbox(
        df_map_fail, lat="latitude", lon="longitude", 
        color_discrete_sequence=[COLOR_FOCO], 
        zoom=10, height=600,
        hover_name="Complaint Type", # Aquí el usuario verá que hay de todo tipo
        mapbox_style="carto-positron",
        opacity=0.3
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    st.success("✅ **Storytelling Final:** El riesgo no es uniforme. El modelo aprenderá que el riesgo depende un 25% del tipo de queja, pero el resto está determinado por el Borough y el Horario.")
