import streamlit as st
import pandas as pd
import plotly.express as px
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

    # PROCESAMIENTO
    df_work = df_raw[df_raw['resolution_time_days'].notna()].copy()
    df_overdue = df_work[df_work['is_overdue_official'] == 1].copy()
    
    st.title("🎯 Dashboard de Auditoría Operativa y Riesgo Legal")
    st.markdown("---")

    # 2. KPIs GLOBALES
    total_casos = len(df_work)
    casos_vencidos = len(df_overdue)
    porcentaje_negligencia = (casos_vencidos / total_casos) if total_casos > 0 else 0
    riesgo_total_usd = df_overdue['estimated_liability_usd'].sum()

    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("Total Reportes", f"{total_casos:,}")
    col_k2.metric("Índice de Negligencia", f"{porcentaje_negligencia:.1%}", delta="Fuera de SLA", delta_color="inverse")
    col_k3.metric("Pasivo Legal Riesgo", f"${riesgo_total_usd/1e6:.1f}M USD", delta="Costo Estimado")

    st.divider()

    # 3. DISTRIBUCIÓN: El Muro Legal
    st.subheader("1. Distribución de Tiempos y Límite Legal")
    agencias_list = sorted(df_work['Agency'].unique())
    agencia_sel = st.selectbox("Selecciona Agencia:", agencias_list, index=0)

    df_ag = df_work[df_work['Agency'] == agencia_sel]
    sla_oficial = df_ag['official_sla_days'].iloc[0]
    
    fig_hist = px.histogram(
        df_ag, x="resolution_time_days", nbins=50, 
        color_discrete_sequence=[COLOR_NEUTRO],
        title=f"Distribución de Respuesta: {agencia_sel}"
    )
    # Sombreado de zona de riesgo
    fig_hist.add_vrect(
        x0=sla_oficial, x1=df_ag['resolution_time_days'].max() if not df_ag.empty else 10, 
        fillcolor=COLOR_FOCO, opacity=0.1, line_width=0,
        annotation_text="ZONA DE RIESGO", annotation_position="top right"
    )
    fig_hist.add_vline(x=sla_oficial, line_dash="dash", line_color=COLOR_FOCO, line_width=3)
    
    # CORRECCIÓN AQUÍ: Se eliminó barcode_mode y se dejó barmode (que es la propiedad real)
    fig_hist.update_layout(
        plot_bgcolor="white", barmode='overlay',
        xaxis_title="Días Hábiles de Resolución",
        yaxis_title="Volumen de Incidentes Reportados"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    # 4. MAGNITUD Y TIEMPO
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Riesgo por Distrito")
        df_boro = df_work.groupby('Borough')['is_overdue_official'].mean().reset_index().sort_values('is_overdue_official')
        fig_boro = px.bar(df_boro, x='is_overdue_official', y='Borough', orientation='h')
        fig_boro.update_traces(marker_color=[COLOR_FOCO if r == df_boro['is_overdue_official'].max() else COLOR_NEUTRO for r in df_boro['is_overdue_official']])
        fig_boro.update_layout(
            plot_bgcolor="white", xaxis_tickformat=".0%",
            xaxis_title="Tasa de Incumplimiento de SLA",
            yaxis_title="Distrito Administrativo"
        )
        st.plotly_chart(fig_boro, use_container_width=True)

    with c2:
        st.subheader("Picos de Riesgo por Horario")
        df_hour = df_work.groupby('created_hour')['is_overdue_official'].mean().reset_index()
        fig_hour = px.area(df_hour, x='created_hour', y='is_overdue_official')
        fig_hour.update_traces(line_color=COLOR_FOCO, fillcolor="rgba(192, 41, 43, 0.2)")
        fig_hour.update_layout(
            plot_bgcolor="white", yaxis_tickformat=".0%",
            xaxis_title="Hora de Creación del Reporte (0–23 h)",
            yaxis_title="Probabilidad de Incumplimiento"
        )
        st.plotly_chart(fig_hour, use_container_width=True)

    st.divider()

    # 6. MAPA
    st.subheader("4. Mapa de Focos de Negligencia")
    fig_map = px.scatter_mapbox(
        df_overdue.sample(n=min(1500, len(df_overdue))), 
        lat="latitude", lon="longitude", color_discrete_sequence=[COLOR_FOCO],
        size="estimated_liability_usd", zoom=9, height=400, mapbox_style="carto-positron"
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    # IMPACTO FINAL
    st.markdown(f"""
        <div style="background-color:{COLOR_FOCO}; padding:25px; border-radius:10px; text-align:center;">
            <h2 style="color:white; margin:0;">PASIVO LEGAL TOTAL</h2>
            <h1 style="color:white; margin:0; font-size:45px;">${riesgo_total_usd/1e6:.1f}M USD</h1>
        </div>
    """, unsafe_allow_html=True)
