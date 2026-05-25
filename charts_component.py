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
    COLOR_FOCO = "#C0292B"   # Rojo: Incumplimiento
    COLOR_NEUTRO = "#718096" # Gris: Contexto
    COLOR_DINERO = "#1E4D2B" # Verde: Éxito/Dinero

    # PROCESAMIENTO INICIAL
    df_work = df_raw[df_raw['resolution_time_days'].notna()].copy()
    df_overdue = df_work[df_work['is_overdue_official'] == 1].copy()
    df_work['overdue_margin_days'] = df_work['resolution_time_days'] - df_work['official_sla_days']

    st.title("🎯 Dashboard de Auditoría Operativa y Riesgo Legal")
    st.markdown("---")

    # 2. KPIs GLOBALES
    total_casos = len(df_work)
    casos_vencidos = len(df_overdue)
    riesgo_total_usd = df_overdue['estimated_liability_usd'].sum()

    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("Total Reportes Analizados", f"{total_casos:,}")
    col_k2.metric("Casos con Negligencia (SLA)", f"{casos_vencidos:,}", delta="Fuera de tiempo")
    col_k3.metric("Pasivo Legal Riesgo", f"${riesgo_total_usd/1e6:.1f}M USD", delta="Costo Estimado")

    st.divider()

    # 3. EXPLICACIÓN DE LA REGLA DE NEGOCIO (EL MURO LEGAL)
    st.subheader("1. ¿Cuándo se considera Negligencia?")
    st.write("Cada agencia tiene un plazo legal (SLA) según el MMR 2019. Al superarlo, se incurre en riesgo de demanda.")
    
    agencias_list = sorted(df_work['Agency'].unique())
    agencia_sel = st.selectbox("Selecciona una agencia para ver su 'Muro Legal':", agencias_list, index=agencias_list.index('DOT') if 'DOT' in agencias_list else 0)

    df_ag = df_work[df_work['Agency'] == agencia_sel]
    sla_oficial = df_ag['official_sla_days'].iloc[0]
    
    fig_hist = px.histogram(df_ag, x="resolution_time_days", nbins=50, color_discrete_sequence=[COLOR_NEUTRO], title=f"Tiempos de Respuesta: {agencia_sel}")
    fig_hist.add_vline(x=sla_oficial, line_dash="dash", line_color=COLOR_FOCO, line_width=3)
    fig_hist.add_annotation(x=sla_oficial, y=0.9, yref="paper", text="LÍMITE LEGAL (MMR)", showarrow=False, font_color=COLOR_FOCO)
    fig_hist.update_layout(plot_bgcolor="white")
    st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()

    # 4. FACTORES DE RIESGO (PROBABILIDAD)
    st.subheader("2. Factores que aumentan la probabilidad de fallo")
    c_left, c_right = st.columns(2)

    with c_left:
        # Riesgo por Borough
        df_boro = df_work.groupby('Borough')['is_overdue_official'].mean().reset_index().sort_values('is_overdue_official')
        fig_boro = px.bar(df_boro, x='is_overdue_official', y='Borough', orientation='h', title="Probabilidad de Incumplimiento por Distrito")
        fig_boro.update_traces(marker_color=[COLOR_FOCO if r == df_boro['is_overdue_official'].max() else COLOR_NEUTRO for r in df_boro['is_overdue_official']])
        fig_boro.update_layout(plot_bgcolor="white", xaxis_tickformat=".0%")
        st.plotly_chart(fig_boro, use_container_width=True)

    with c_right:
        # Riesgo por Hora
        df_hour = df_work.groupby('created_hour')['is_overdue_official'].mean().reset_index()
        fig_hour = px.line(df_hour, x='created_hour', y='is_overdue_official', title="Riesgo según Hora de Creación")
        fig_hour.update_traces(line_color=COLOR_FOCO, line_width=3)
        fig_hour.update_layout(plot_bgcolor="white", yaxis_tickformat=".0%")
        st.plotly_chart(fig_hour, use_container_width=True)

    st.divider()

    # 5. DESGLOSE FINANCIERO (LO NUEVO)
    st.subheader("3. Análisis de Responsabilidad Económica")
    st.write("Desglose del impacto financiero si los casos vencidos terminan en indemnizaciones legales.")

    df_agency_money = df_overdue.groupby('Agency').agg(
        casos_fuera=('Unique Key', 'count'),
        costo_unitario=('avg_negligence_cost', 'first'),
        pasivo_total=('estimated_liability_usd', 'sum')
    ).reset_index().sort_values('pasivo_total', ascending=False)

    col_t, col_p = st.columns([0.6, 0.4])
    with col_t:
        st.dataframe(df_agency_money.rename(columns={
            'Agency': 'Agencia', 'casos_fuera': 'Casos Vencidos', 
            'costo_unitario': 'Costo x Demanda', 'pasivo_total': 'Riesgo Total'
        }).style.format({'Costo x Demanda': '${:,.0f}', 'Riesgo Total': '${:,.0f}'}), use_container_width=True)

    with col_p:
        fig_tree = px.treemap(df_agency_money, path=['Agency'], values='pasivo_total', color='pasivo_total', color_continuous_scale='Reds')
        fig_tree.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_tree, use_container_width=True)

    st.divider()

    # 6. MAPA Y CIERRE
    st.subheader("4. Mapa de Focos de Negligencia")
    fig_map = px.scatter_mapbox(
        df_overdue.sample(n=min(3000, len(df_overdue))), 
        lat="latitude", lon="longitude", 
        color="Agency", size="estimated_liability_usd",
        zoom=10, height=600, mapbox_style="carto-positron"
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    # CLÍMAX FINAL
    st.markdown(f"""
        <div style="background-color:#C0292B; padding:30px; border-radius:15px; text-align:center; margin-top:20px;">
            <h2 style="color:white; margin:0;">PASIVO LEGAL TOTAL EN RIESGO</h2>
            <h1 style="color:white; margin:0; font-size:50px;">${riesgo_total_usd/1e6:.1f} Millones USD</h1>
            <p style="color:white; opacity:0.8;">Estimación basada en negligencia operativa sobre SLAs oficiales de NYC en 2019</p>
        </div>
    """, unsafe_allow_html=True)
