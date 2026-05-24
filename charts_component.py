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

    # Colores de marca (Ingeniería de la Atención)
    COLOR_FOCO = "#C0292B"   # Rojo: Incumplimiento / Riesgo
    COLOR_NEUTRO = "#718096" # Gris: Contexto
    COLOR_EXITO = "#28A745"  # Verde: Cumplimiento

    st.header("🎯 Estrategia de Modelado: Predicción de Incumplimiento (SLA)")
    
    # 1. EXPLICACIÓN VISUAL DEL TARGET (PARA EL COMITÉ)
    st.subheader("1. ¿Qué estamos intentando predecir?")
    st.markdown("""
    Para que el modelo sea justo, calculamos el **Percentil 75 (P75)** de cada categoría. 
    A continuación vemos el ejemplo real de la categoría **'MOSQUITOES'**:
    """)

    # --- Gráfica de concepto: El porqué del 75% ---
    ejemplo_cat = "MOSQUITOES"
    df_ex = df_raw[df_raw['Complaint Type'] == ejemplo_cat].dropna(subset=['resolution_time_days'])
    
    if not df_ex.empty:
        umbral_p75 = df_ex['p75_resolution_time_days'].iloc[0]
        
        fig_concept = px.histogram(
            df_ex, x="resolution_time_days", nbins=50,
            title=f"Distribución de Tiempos para {ejemplo_cat}",
            color_discrete_sequence=[COLOR_NEUTRO],
            labels={'resolution_time_days': 'Días transcurridos'}
        )
        
        # Añadimos la línea "pared" del P75
        fig_concept.add_vline(x=umbral_p75, line_dash="dash", line_color=COLOR_FOCO, line_width=3)
        
        # Anotaciones para explicar el 75/25
        fig_concept.add_annotation(x=umbral_p75/2, y=5, text="75% Casos 'Normales'<br>(Cumplen)", showarrow=False, font=dict(color=COLOR_EXITO))
        fig_concept.add_annotation(x=umbral_p75*1.2, y=5, text="25% Casos CRÍTICOS<br>(Incumplen)", showarrow=False, font=dict(color=COLOR_FOCO))
        
        fig_concept.update_layout(plot_bgcolor="white", showlegend=False)
        st.plotly_chart(fig_concept, use_container_width=True)
        st.info(f"💡 **Regla de Negocio:** Para {ejemplo_cat}, si la queja supera los **{umbral_p75:.1f} días**, el sistema dispara una alerta de incumplimiento. **Este es el '1' que nuestro modelo aprenderá a predecir.**")

    st.divider()

    # 2. COMPARATIVA DE UMBRALES (LA DIVERSIDAD DEL NEGOCIO)
    st.subheader("2. Cada queja tiene su propia 'valla'")
    st.write("No podemos medir un bache igual que una fuga de agua. Aquí vemos los días límite (P75) que definen el fallo para el Top 10 de quejas:")

    df_work = df_raw[df_raw['p75_resolution_time_days'].notna()].copy()
    df_thresholds = df_work.groupby('Complaint Type')['p75_resolution_time_days'].first().reset_index()
    df_thresholds = df_thresholds.sort_values('p75_resolution_time_days', ascending=True).tail(10)

    fig_thr = px.bar(df_thresholds, x='p75_resolution_time_days', y='Complaint Type', orientation='h')
    fig_thr.update_traces(marker_color=COLOR_NEUTRO, opacity=0.7)
    # Resaltar la más lenta
    fig_thr.data[0].marker.color = [COLOR_FOCO if (x == df_thresholds['p75_resolution_time_days'].max()) else COLOR_NEUTRO for x in df_thresholds['p75_resolution_time_days']]
    
    fig_thr.update_layout(plot_bgcolor="white", xaxis_title="Días límite para el SLA (P75)")
    st.plotly_chart(fig_thr, use_container_width=True)

    # 3. FACTORES QUE INFLUYEN EN LA PROBABILIDAD (FEATURES)
    st.subheader("3. Factores de Riesgo: ¿Dónde y Cuándo fallamos?")
    
    col_left, col_right = st.columns(2)

    with col_left:
        # Riesgo por Distrito
        df_boro_risk = df_work.groupby('Borough')['is_sla_non_compliant'].mean().reset_index()
        df_boro_risk = df_boro_risk.sort_values('is_sla_non_compliant', ascending=True)
        
        fig_boro = px.bar(df_boro_risk, x='is_sla_non_compliant', y='Borough', orientation='h',
                          title="Probabilidad de Incumplimiento por Borough")
        # Ingeniería de la atención: Pintar de rojo solo si supera el 25% (que es el promedio teórico)
        fig_boro.update_traces(marker_color=[COLOR_FOCO if r > 0.25 else COLOR_NEUTRO for r in df_boro_risk['is_sla_non_compliant']])
        fig_boro.update_layout(plot_bgcolor="white", xaxis_tickformat=".0%")
        st.plotly_chart(fig_boro, use_container_width=True)

    with col_right:
        # Riesgo por Hora
        df_hour_risk = df_work.groupby('created_hour')['is_sla_non_compliant'].mean().reset_index()
        fig_hour = px.line(df_hour_risk, x='created_hour', y='is_sla_non_compliant',
                           title="Riesgo de Incumplimiento según Hora")
        fig_hour.update_traces(line_color=COLOR_FOCO, line_width=4)
        fig_hour.update_layout(plot_bgcolor="white", yaxis_tickformat=".0%", yaxis_title="Probabilidad de Fallo")
        st.plotly_chart(fig_hour, use_container_width=True)

    st.divider()

    # 4. GEOGRAFÍA DEL FALLO (CONTRASTE FIGURA-FONDO)
    st.subheader("4. Focos Geográficos: ¿Dónde se concentra la ineficiencia?")
    st.write("Para reducir el ruido, visualizamos **exclusivamente** los incidentes que ya han incumplido su SLA.")
    
    df_fail = df_work[df_work['is_sla_non_compliant'] == 1]
    df_map_fail = df_fail.sample(n=min(5000, len(df_fail)))

    fig_map = px.scatter_mapbox(
        df_map_fail, lat="latitude", lon="longitude", 
        color_discrete_sequence=[COLOR_FOCO], 
        zoom=10, height=600,
        mapbox_style="carto-positron",
        opacity=0.3
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    st.success("""
    **Conclusión del EDA para el Modelado:** 
    1. El **Target** es balanceado (75/25) pero adaptado a cada categoría.
    2. La **Hora** y el **Borough** muestran variaciones en la probabilidad, lo que los valida como predictores clave.
    3. Existen clusters geográficos de ineficiencia visibles en el mapa.
    """)
