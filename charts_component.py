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
    
    st.title("🎯 Dashboard de Auditoría Operativa y Riesgo Legal")
    st.markdown("---")

    # DISTRIBUCIÓN Y HORARIO APILADAS
    agencias_list = sorted(df_work['Agency'].unique())
    agencia_sel = st.selectbox("Selecciona Agencia:", agencias_list, index=0)

    st.subheader("Distribución de Tiempos y Límite Legal")
    df_ag = df_work[df_work['Agency'] == agencia_sel]
    sla_oficial = df_ag['official_sla_days'].iloc[0]

    fig_hist = px.histogram(
        df_ag, x="resolution_time_days", nbins=50,
        color_discrete_sequence=[COLOR_NEUTRO],
        title=f"Distribución de Respuesta: {agencia_sel}"
    )
    fig_hist.add_vrect(
        x0=sla_oficial, x1=df_ag['resolution_time_days'].max() if not df_ag.empty else 10,
        fillcolor=COLOR_FOCO, opacity=0.1, line_width=0,
        annotation_text="ZONA DE RIESGO", annotation_position="top right"
    )
    fig_hist.add_vline(x=sla_oficial, line_dash="dash", line_color=COLOR_FOCO, line_width=3)
    fig_hist.update_layout(
        plot_bgcolor="white", barmode='overlay',
        xaxis_title="Días Hábiles de Resolución",
        yaxis_title="Volumen de Incidentes Reportados"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

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
