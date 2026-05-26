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

    # Paleta de Colores "Ingeniería de la Atención" (Basada en la guía)
    COLOR_FOCO = "#C0292B"   # Rojo: Incumplimiento (Desviación)
    COLOR_NEUTRO = "#718096" # Gris: Contexto
    COLOR_DINERO = "#1E4D2B" # Verde: Éxito/Dinero
    COLOR_ACUMULADO = "#2B6CB0" # Azul para líneas de tendencia

    # PROCESAMIENTO
    df_work = df_raw[df_raw['resolution_time_days'].notna()].copy()
    df_overdue = df_work[df_work['is_overdue_official'] == 1].copy()
    
    st.title("🎯 Dashboard de Auditoría Operativa y Riesgo Legal")
    st.markdown("---")

    # 2. KPIs GLOBALES (Más informativos)
    total_casos = len(df_work)
    casos_vencidos = len(df_overdue)
    porcentaje_negligencia = (casos_vencidos / total_casos) if total_casos > 0 else 0
    riesgo_total_usd = df_overdue['estimated_liability_usd'].sum()

    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("Total Reportes", f"{total_casos:,}")
    col_k2.metric("Índice de Negligencia", f"{porcentaje_negligencia:.1%}", delta="Fuera de SLA", delta_color="inverse")
    col_k3.metric("Pasivo Legal Riesgo", f"${riesgo_total_usd/1e6:.1f}M USD", delta="Costo Estimado")

    st.divider()

    # 3. DISTRIBUCIÓN: El Muro Legal (Mejorado con sombreado de riesgo)
    st.subheader("1. Distribución de Tiempos y Límite Legal")
    
    agencias_list = sorted(df_work['Agency'].unique())
    agencia_sel = st.selectbox("Selecciona Agencia:", agencias_list, index=agencias_list.index('DOT') if 'DOT' in agencias_list else 0)

    df_ag = df_work[df_work['Agency'] == agencia_sel]
    sla_oficial = df_ag['official_sla_days'].iloc[0]
    
    fig_hist = px.histogram(
        df_ag, x="resolution_time_days", nbins=50, 
        color_discrete_sequence=[COLOR_NEUTRO],
        title=f"Distribución de Respuesta: {agencia_sel}"
    )
    # Resaltar la zona de negligencia (lo que está a la derecha del SLA)
    fig_hist.add_vrect(
        x0=sla_oficial, x1=df_ag['resolution_time_days'].max(), 
        fillcolor=COLOR_FOCO, opacity=0.1, line_width=0,
        annotation_text="ZONA DE RIESGO LEGAL", annotation_position="top right"
    )
    fig_hist.add_vline(x=sla_oficial, line_dash="dash", line_color=COLOR_FOCO, line_width=3)
    fig_hist.update_layout(plot_bgcolor="white", barcode_mode='overlay')
    st.plotly_chart(fig_hist, use_container_width=True)

    # 4. MAGNITUD Y CAMBIOS EN EL TIEMPO
    col_left, col_right = st.columns(2)

    with col_left:
        # MAGNITUD: Barras horizontales ordenadas (Clasificación según la guía)
        st.subheader("Riesgo por Distrito")
        df_boro = df_work.groupby('Borough')['is_overdue_official'].mean().reset_index().sort_values('is_overdue_official')
        fig_boro = px.bar(
            df_boro, x='is_overdue_official', y='Borough', orientation='h',
            title="Probabilidad de Incumplimiento"
        )
        # Resaltar solo el más alto
        fig_boro.update_traces(marker_color=[COLOR_FOCO if r == df_boro['is_overdue_official'].max() else COLOR_NEUTRO for r in df_boro['is_overdue_official']])
        fig_boro.update_layout(plot_bgcolor="white", xaxis_tickformat=".0%", xaxis_title="% Casos Vencidos")
        st.plotly_chart(fig_boro, use_container_width=True)

    with col_right:
        # CAMBIOS EN EL TIEMPO: Gráfico de área (Fluidez y tendencia)
        st.subheader("Riesgo por Hora de Creación")
        df_hour = df_work.groupby('created_hour')['is_overdue_official'].mean().reset_index()
        fig_hour = px.area( # Cambiado de línea a área para dar más peso visual al riesgo
            df_hour, x='created_hour', y='is_overdue_official',
            title="Picos de Negligencia por Horario"
        )
        fig_hour.update_traces(line_color=COLOR_FOCO, fillcolor="rgba(192, 41, 43, 0.2)")
        fig_hour.update_layout(plot_bgcolor="white", yaxis_tickformat=".0%", yaxis_title="% Riesgo")
        st.plotly_chart(fig_hour, use_container_width=True)

    st.divider()

    # 5. ANÁLISIS ECONÓMICO: PARETO TOP 5 (Reemplaza a las cajas/treemap)
    # Basado en la categoría de "Magnitud" y "Parte de un todo" de forma jerárquica
    st.subheader("3. Análisis de Responsabilidad Económica (Pareto)")
    st.write("Identificación del 80/20: Agencias que concentran la mayor parte del pasivo total.")

    df_agency_money = df_overdue.groupby('Agency').agg(
        pasivo_total=('estimated_liability_usd', 'sum')
    ).reset_index().sort_values('pasivo_total', ascending=False)

    top_5 = df_agency_money.head(5).copy()
    total_pasivo = df_agency_money['pasivo_total'].sum()
    top_5['pct_acumulado'] = (top_5['pasivo_total'].cumsum() / total_pasivo)

    fig_pareto = go.Figure()
    # Barras de magnitud
    fig_pareto.add_trace(go.Bar(
        x=top_5['Agency'], y=top_5['pasivo_total'],
        name="Pasivo USD", marker_color=COLOR_DINERO,
        text=[f"${v/1e6:.1f}M" for v in top_5['pasivo_total']], textposition='outside'
    ))
    # Línea de acumulado (Clasificación/Correlación)
    fig_pareto.add_trace(go.Scatter(
        x=top_5['Agency'], y=top_5['pct_acumulado'] * top_5['pasivo_total'].max() * 1.2, # Escala visual
        name="% Acumulado", line=dict(color=COLOR_ACUMULADO, width=4), yaxis="y2"
    ))

    fig_pareto.update_layout(
        title="Top 5 Agencias por Impacto Financiero",
        yaxis=dict(title="Dólares (USD)", showgrid=False),
        yaxis2=dict(title="Porcentaje Acumulado", overlaying='y', side='right', range=[0, 1.1], tickformat=".0%"),
        plot_bgcolor="white", showlegend=False
    )
    st.plotly_chart(fig_pareto, use_container_width=True)

    st.divider()

    # 6. ESPACIAL: Mapa (Más limpio)
    st.subheader("4. Mapa de Focos de Negligencia")
    fig_map = px.scatter_mapbox(
        df_overdue.sample(n=min(2000, len(df_overdue))), 
        lat="latitude", lon="longitude", 
        color_discrete_sequence=[COLOR_FOCO], # Color único para enfatizar "problema"
        size="estimated_liability_usd",
        zoom=10, height=500, mapbox_style="carto-positron",
        title="Ubicación Geográfica de Casos Críticos"
    )
    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    # CIERRE CON IMPACTO
    st.markdown(f"""
        <div style="background-color:{COLOR_FOCO}; padding:30px; border-radius:15px; text-align:center;">
            <h2 style="color:white; margin:0;">PASIVO LEGAL TOTAL EN RIESGO</h2>
            <h1 style="color:white; margin:0; font-size:50px;">${riesgo_total_usd/1e6:.1f} Millones USD</h1>
        </div>
    """, unsafe_allow_html=True)
