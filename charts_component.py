import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from s3_utils import load_from_s3

def render_dynamic_charts():
    # 1. CARGA DE DATOS (Capa Gold con SLAs Oficiales y Costos)
    prefix_gold = "gold/enhanced_for_streamlit_eda/"
    df_raw = load_from_s3(prefix=prefix_gold)
    
    if df_raw is None or df_raw.empty:
        st.error("No se pudieron cargar los datos de la capa Gold.")
        return

    # Paleta de Colores "Ingeniería de la Atención"
    COLOR_FOCO = "#C0292B"   # Rojo: Peligro / Incumplimiento
    COLOR_NEUTRO = "#718096" # Gris: Contexto
    COLOR_DINERO = "#1E4D2B" # Verde Oscuro: Impacto Financiero
    
    # 2. CABECERA Y STORYTELLING
    st.header("⚖️ Auditoría de Cumplimiento Legal y Riesgo Financiero")
    st.markdown(f"""
    **Pregunta de Negocio:** ¿Qué probabilidad hay de que la ciudad sea demandada por negligencia operativa?
    
    En este análisis, ya no usamos promedios estadísticos. Comparamos la realidad contra los tiempos de respuesta del **Mayor's Management Report 2019** 
    y monetizamos el riesgo usando el **Annual Claims Report** de la Contraloría.
    """)

    # 3. KPIs FINANCIEROS Y OPERATIVOS
    # Filtramos casos cerrados para medir cumplimiento real
    df_work = df_raw[df_raw['resolution_time_days'].notna()].copy()
    
    total_casos = len(df_work)
    casos_vencidos = df_work[df_work['is_overdue_official'] == 1].shape[0]
    riesgo_total_usd = df_work['estimated_liability_usd'].sum()
    tasa_incumplimiento = (casos_vencidos / total_casos) if total_casos > 0 else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Casos Vencidos (SLA Oficial)", f"{casos_vencidos:,}", delta="Riesgo de Negligencia")
    k2.metric("Tasa de Incumplimiento", f"{tasa_incumplimiento:.1%}")
    k3.metric("Riesgo de Pasivo Legal", f"${riesgo_total_usd/1e6:.1f}M USD", delta="Impacto Estimado", delta_color="inverse")

    st.divider()

    # 4. EXPLICACIÓN DEL "MURO LEGAL" (HISTOGRAMA INTERACTIVO)
    st.subheader("1. La Barrera de la Negligencia")
    st.write("Selecciona una agencia para ver qué tan lejos de la ley (SLA) se encuentran sus respuestas actuales.")
    
    agencias_disponibles = sorted(df_work['Agency'].unique())
    agencia_sel = st.selectbox("Analizar Agencia:", agencias_disponibles, index=agencias_disponibles.index('DOT') if 'DOT' in agencias_disponibles else 0)

    df_agencia = df_work[df_work['Agency'] == agencia_sel]
    sla_oficial = df_agencia['official_sla_days'].iloc[0]
    costo_promedio = df_agencia['avg_negligence_cost'].iloc[0]

    fig_concept = px.histogram(
        df_agencia, x="resolution_time_days", nbins=50,
        title=f"Distribución de Tiempos: {agencia_sel}",
        color_discrete_sequence=[COLOR_NEUTRO],
        labels={'resolution_time_days': 'Días de Resolución'}
    )
    # Línea del SLA oficial del MMR 2019
    fig_concept.add_vline(x=sla_oficial, line_dash="dash", line_color=COLOR_FOCO, line_width=3)
    fig_concept.add_annotation(x=sla_oficial, y=0.9, yref="paper", text=f"LÍMITE LEGAL: {sla_oficial} días", showarrow=False, font_color=COLOR_FOCO)
    
    fig_concept.update_layout(plot_bgcolor="white")
    st.plotly_chart(fig_concept, use_container_width=True)
    st.info(f"💰 **Análisis para {agencia_sel}:** Cada caso a la derecha de la línea roja representa un riesgo promedio de **${costo_promedio:,.0f} USD** en indemnizaciones.")

    st.divider()

    # 5. ANÁLISIS DE RIESGO ECONÓMICO POR DISTRITO
    st.subheader("2. Mapa del Riesgo Financiero (Liability)")
    st.write("Visualizamos solo los tickets vencidos. El tamaño del punto indica el costo promedio de la demanda según la agencia.")

    df_overdue = df_work[df_work['is_overdue_official'] == 1]
    # Muestra representativa
    df_map = df_overdue.sample(n=min(3000, len(df_overdue)))

    fig_map = px.scatter_mapbox(
        df_map, lat="latitude", lon="longitude", 
        color="Agency", # Colores por agencia para ver quién domina la zona
        size="estimated_liability_usd", # Más grande = más caro fallar ahí
        hover_name="Complaint Type",
        hover_data={"estimated_liability_usd": ':,.0f', "resolution_time_days": ':.1f'},
        zoom=10, height=600,
        mapbox_style="carto-positron"
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    # 6. COMPARATIVA DE IMPACTO POR AGENCIA
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("3. Probabilidad de Fallo por Distrito")
        df_boro = df_work.groupby('Borough')['is_overdue_official'].mean().reset_index()
        df_boro = df_boro.sort_values('is_overdue_official', ascending=True)
        fig_boro = px.bar(df_boro, x='is_overdue_official', y='Borough', orientation='h',
                          title="Tasa de Incumplimiento Oficial",
                          color_discrete_sequence=[COLOR_NEUTRO])
        # Resaltar los que superan el 30%
        fig_boro.update_traces(marker_color=[COLOR_FOCO if r > 0.3 else COLOR_NEUTRO for r in df_boro['is_overdue_official']])
        fig_boro.update_layout(xaxis_tickformat=".0%", plot_bgcolor="white")
        st.plotly_chart(fig_boro, use_container_width=True)

    with col_b:
        st.subheader("4. Pasivo Total en Riesgo por Agencia")
        df_money = df_work.groupby('Agency')['estimated_liability_usd'].sum().reset_index()
        df_money = df_money.sort_values('estimated_liability_usd', ascending=True).tail(10)
        fig_money = px.bar(df_money, x='estimated_liability_usd', y='Agency', orientation='h',
                           title="Riesgo Acumulado (USD)",
                           color_discrete_sequence=[COLOR_DINERO])
        fig_money.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig_money, use_container_width=True)

    st.success(f"""
    **Conclusión Estratégica:** 
    Aunque el volumen de quejas sea alto en toda la ciudad, el riesgo financiero se concentra en la agencia **{df_money.iloc[-1]['Agency']}**, 
    donde el incumplimiento del SLA oficial representa el mayor pasivo legal potencial.
    """)
