import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from s3_utils import load_from_s3

def render_dynamic_charts():
    # 1. CARGA DE DATOS
    prefix_gold = "gold/enhanced_for_streamlit_eda/"
    df_raw = load_from_s3(prefix=prefix_gold)
    
    if df_raw is None or df_raw.empty:
        st.error("No se pudieron cargar los datos de la capa Gold.")
        return

    # Paleta de Colores "Ingeniería de la Atención"
    COLOR_FOCO = "#C0292B"   # Rojo: Incumplimiento Crítico
    COLOR_DINERO = "#1E4D2B" # Verde: Impacto Económico
    COLOR_NEUTRO = "#EDF2F7" # Gris claro: Fondo / Base

    # 2. PROCESAMIENTO DE IMPACTO INDIVIDUAL
    # Filtramos casos cerrados para tener cálculos reales
    df_work = df_raw[df_raw['resolution_time_days'].notna()].copy()
    
    # Calculamos el "Exceso de Tiempo" (Margen de Negligencia)
    df_work['overdue_margin_days'] = df_work['resolution_time_days'] - df_work['official_sla_days']
    # Solo nos interesan los que excedieron el límite
    df_overdue = df_work[df_work['is_overdue_official'] == 1].copy()

    # 3. STORYTELLING Y KPIs
    st.header("💰 Informe de Riesgo Financiero por Ineficiencia Operativa")
    st.markdown("""
    Este análisis cuantifica la **negligencia institucional**. Cada registro que excede el tiempo de respuesta oficial del 
    **MMR 2019** se convierte en un punto de exposición legal según el **Comptroller Claims Report**.
    """)

    total_negligencias = len(df_overdue)
    riesgo_total_usd = df_overdue['estimated_liability_usd'].sum()
    promedio_retraso = df_overdue['overdue_margin_days'].mean()

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric("Incidentes con Negligencia Legal", f"{total_negligencias:,}", "Superaron SLA")
    with col_kpi2:
        st.metric("Promedio de Exceso de Tiempo", f"{promedio_retraso:.1f} días", "Sobre el límite legal")
    with col_kpi3:
        st.metric("Pasivo Económico Acumulado", f"${riesgo_total_usd/1e6:.1f}M USD", "Riesgo en demandas")

    st.divider()

    # 4. GRÁFICA DE DOMINANCIA VISUAL: RANKING DE PASIVOS POR AGENCIA
    st.subheader("1. ¿Quién está comprometiendo más presupuesto?")
    st.write("A continuación, el cálculo final del riesgo acumulado por cada agencia. El color indica el volumen de casos vencidos.")

    # Agrupamos por Agencia para el cálculo final
    df_agency_risk = df_overdue.groupby('Agency').agg({
        'Unique Key': 'count',
        'estimated_liability_usd': 'sum',
        'overdue_margin_days': 'mean'
    }).reset_index().rename(columns={'Unique Key': 'Casos Vencidos'})

    df_agency_risk = df_agency_risk.sort_values('estimated_liability_usd', ascending=True)

    fig_risk = px.bar(
        df_agency_risk, 
        x='estimated_liability_usd', 
        y='Agency', 
        orientation='h',
        color='Casos Vencidos',
        color_continuous_scale='Reds',
        labels={'estimated_liability_usd': 'Riesgo Total (USD)', 'Agency': 'Agencia'},
        title="Impacto Económico Total por Incumplimiento"
    )
    
    fig_risk.update_layout(plot_bgcolor="white", coloraxis_showscale=False)
    st.plotly_chart(fig_risk, use_container_width=True)

    # 5. ANÁLISIS DE "GRAVEDAD" (SCATTER PLOT)
    st.subheader("2. Matriz de Severidad: Tiempo vs. Dinero")
    st.write("Cada punto es una categoría de queja. Los que están arriba a la derecha son los más peligrosos: tardan mucho y son caros.")

    df_complaint_risk = df_overdue.groupby('Complaint Type').agg({
        'overdue_margin_days': 'mean',
        'estimated_liability_usd': 'sum',
        'Agency': 'first'
    }).reset_index()

    fig_scatter = px.scatter(
        df_complaint_risk,
        x='overdue_margin_days',
        y='estimated_liability_usd',
        size='estimated_liability_usd',
        color='Agency',
        hover_name='Complaint Type',
        title="Categorías por Exceso de Tiempo y Pasivo Total",
        labels={'overdue_margin_days': 'Días de Retraso Extra (Promedio)', 'estimated_liability_usd': 'Riesgo Financiero Total'},
        height=500
    )
    fig_scatter.update_layout(plot_bgcolor="#F8F9FA")
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.divider()

    # 6. EL MAPA DE LA NEGLIGENCIA (CONTRASTE FIGURA-FONDO)
    st.subheader("3. Localización de los 'Puntos de Negligencia'")
    st.write("Visualización de las quejas vencidas. La intensidad del rojo muestra dónde la ciudad está siendo 'más lenta' legalmente.")
    
    # Usamos opacidad baja para resaltar densidad
    fig_map = px.scatter_mapbox(
        df_overdue.sample(n=min(5000, len(df_overdue))), 
        lat="latitude", lon="longitude", 
        color="overdue_margin_days", # El color ahora representa cuántos días llevan de retraso
        size="avg_negligence_cost", # El tamaño representa el costo de la agencia
        color_continuous_scale='OrRd',
        zoom=10, height=600,
        mapbox_style="carto-positron",
        title="Mapa de Calor de Retrasos Acumulados"
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    # 7. CONCLUSIÓN DE CIENCIA DE DATOS
    st.success(f"""
    **Conclusión del Riesgo:**
    - Se identificaron **{total_negligencias:,}** incidentes que operan bajo negligencia legal.
    - El riesgo financiero no es proporcional al número de quejas, sino a la combinación de **Agencia** y **Retraso**.
    - El modelo predictivo debe priorizar las quejas de **{df_agency_risk.iloc[-1]['Agency']}** para mitigar un pasivo de **${df_agency_risk.iloc[-1]['estimated_liability_usd']/1e6:.1f}M USD**.
    """)
