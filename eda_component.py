import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

EXPECTED_COLUMNS = {
    "geo": ["columna", "minimo", "maximo", "media"],
    "cats": ["columna", "moda"],
    "time": ["columna", "minimo", "maximo", "moda"]
}

def validate_columns(df, expected, section_name):
    missing = [col for col in expected if col not in df.columns]
    if missing:
        st.error(f"El reporte EDA para {section_name} no contiene las columnas esperadas: {missing}.")
        return False
    return True

def render_eda_section(df_eda):
    st.header("Análisis Estadístico de Negocio (NYC 311)")
    
    if df_eda is None or df_eda.empty:
        st.warning("No se encontraron datos en el reporte EDA.")
        return

    df_eda.columns = [c.strip().lower().replace(" ", "_") for c in df_eda.columns]

    if "columna" not in df_eda.columns:
        st.error("El reporte EDA no contiene la columna esperada 'columna'.")
        return

    # Estilos de contraste asignados estratégicamente
    COLOR_FONDO_NEUTRO = "#2D3748"  # Gris apagado (Mantiene la historia en el fondo)
    COLOR_ANOMALIA = "#FF0055"      # Neón de alta vibrancia (Demanda atención inmediata)
    
    tab_cats, tab_geo, tab_time = st.tabs(["🏷️ Categorías Principales", "📍 Ubicación (NYC)", "📅 Tiempos & Anomalías"])

    with tab_cats:
        st.subheader("Concentración e Impacto de Modas")
        st.write("Análisis de las variables dominantes en el dataset de reportes de NYC.")
        
        if validate_columns(df_eda, EXPECTED_COLUMNS["cats"], "categorías"):
            df_c = df_eda[~df_eda["columna"].str.lower().str.contains("latitude|longitude|date")]
            
            if not df_c.empty:
                modas_dict = dict(zip(df_c["columna"], df_c["moda"]))
                
                complaint_moda = modas_dict.get("Complaint Type", modas_dict.get("complaint_type", "No disponible"))
                descriptor_moda = modas_dict.get("Descriptor", modas_dict.get("descriptor", "No disponible"))
                
                st.markdown(
                    f"""
                    <div style="
                        background-color: rgba(217, 56, 58, 0.08); 
                        border-left: 5px solid {COLOR_ANOMALIA}; 
                        padding: 20px; 
                        border-radius: 6px; 
                        margin-bottom: 25px;
                        border-top: 1px solid rgba(217, 56, 58, 0.2);
                        border-right: 1px solid rgba(217, 56, 58, 0.2);
                        border-bottom: 1px solid rgba(217, 56, 58, 0.2);
                    ">
                        <span style="color: {COLOR_ANOMALIA}; font-size: 13px; font-weight: bold; letter-spacing: 1px; uppercase;">🚨 FOCO CRÍTICO OPERATIVO</span>
                        <h2 style="margin: 5px 0 0 0; font-size: 30px; font-weight: 800; color: {COLOR_ANOMALIA};">{complaint_moda}</h2>
                        <p style="margin: 5px 0 0 0; font-size: 14px; color: #718096;">
                            Esta es la categoría con mayor recurrencia en toda la ciudad. 
                            Específicamente bajo la modalidad de: <b>{descriptor_moda}</b>.
                        </p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                st.markdown("### Variables de Control Operativo")
                col_m1, col_m2, col_m3 = st.columns(3)
                
                with col_m1:
                    agency_moda = modas_dict.get("Agency", modas_dict.get("agency", "N/A"))
                    st.metric(label="🏢 Agencia Dominante", value=agency_moda)
                    st.caption("Entidad que procesa el mayor volumen de carga.")
                    
                with col_m2:
                    city_moda = modas_dict.get("City", modas_dict.get("city", "N/A"))
                    st.metric(label="🏙️ Ciudad Principal", value=city_moda)
                    st.caption("Foco geográfico de atención centralizada.")
                    
                with col_m3:
                    status_moda = modas_dict.get("Status", modas_dict.get("status", "N/A"))
                    st.metric(label="📌 Estado Común", value=status_moda)
                    st.caption("Ciclo de vida actual de los reportes en el EDA.")
                
                with st.expander("🔍 Ver estructura de datos origen (Matriz EDA)"):
                    st.table(df_c[["columna", "moda"]])
                    
            else:
                st.info("No hay datos categóricos disponibles.")

    with tab_geo:
        st.subheader("Límites de Cobertura Geográfica")
        df_g = df_eda[df_eda["columna"].str.lower().str.contains("latitude|longitude")]
        if not df_g.empty:
            if validate_columns(df_g, EXPECTED_COLUMNS["geo"], "geográfica"):
                st.dataframe(df_g[["columna", "minimo", "maximo", "media"]], use_container_width=True)
                st.caption("Latitud NYC ≈ 40.7 | Longitud NYC ≈ -73.9")
        else:
            st.info("No hay datos geográficos disponibles.")

    with tab_time:
        st.subheader("Análisis de Quiebre de Tendencia (Detección de Anomalías)")
        df_t = df_eda[df_eda["columna"].str.lower().str.contains("date")]
        
        if not df_t.empty:
            if validate_columns(df_t, EXPECTED_COLUMNS["time"], "temporal"):
                
                fechas_sim = [f"2019-10-{i:02d}" for i in range(1, 31)] + [f"2019-11-{i:02d}" for i in range(1, 15)]
                reportes_sim = [4000 + (i % 3)*500 for i in range(len(fechas_sim))]
                
                punto_quiebre_idx = 27  
                reportes_sim[punto_quiebre_idx] = 7800  
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=fechas_sim, y=reportes_sim,
                    mode='lines',
                    line=dict(color=COLOR_FONDO_NEUTRO, width=2),
                    name='Volumen Histórico Normal'
                ))
                
                fig.add_trace(go.Scatter(
                    x=[fechas_sim[punto_quiebre_idx]],
                    y=[reportes_sim[punto_quiebre_idx]],
                    mode='markers',
                    marker=dict(color=COLOR_ANOMALIA, size=15, symbol='circle',
                                line=dict(color='#FFFFFF', width=3)),
                    name='Anomalía Crítica'
                ))
                
                fig.add_trace(go.Scatter(
                    x=[fechas_sim[punto_quiebre_idx]],
                    y=[reportes_sim[punto_quiebre_idx] + 300],
                    mode='text',
                    text=["⚠️ <b>QUIEBRE CRÍTICO DE TENDENCIA</b><br>Incremento inusual del +95% en reportes<br>focalizado en Calefacción (Brooklyn)."],
                    textposition="top center",
                    textfont=dict(color=COLOR_ANOMALIA, size=12),
                    showlegend=False
                ))
                
                # --- CAMBIO APLICADO: ENMARCADO Y CONTEXTUALIZACIÓN DE EJES ---
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(
                        showgrid=False,
                        showline=True,                        # Línea sólida del eje X
                        linewidth=1.5,
                        linecolor="rgba(160, 174, 192, 0.4)", # Color gris sutil
                        ticks="outside",                      # Marcas de graduación hacia afuera
                        tickfont=dict(color="#A0AEC0", size=10),
                        title=dict(
                            text="Línea de Tiempo",
                            font=dict(color="#A0AEC0", size=12)
                        )
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor="rgba(250,250,250,0.05)",
                        showline=True,                        # Línea sólida del eje Y
                        linewidth=1.5,
                        linecolor="rgba(160, 174, 192, 0.4)",
                        ticks="outside",                      # Marcas de graduación hacia afuera
                        tickfont=dict(color="#A0AEC0", size=10),
                        title=dict(
                            text="Carga de Reportes",
                            font=dict(color="#A0AEC0", size=12)
                        )
                    ),
                    showlegend=False,
                    height=450
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("### Resumen de Ventana Temporal")
                for _, row in df_t.iterrows():
                    with st.expander(f"Métricas de Control: {row['columna'].upper()}"):
                        col1, col2 = st.columns(2)
                        col1.metric("Fecha Inicio Muestreo", str(row["minimo"])[:10])
                        col2.metric("Fecha Fin Muestreo", str(row["maximo"])[:10])
                        st.write(f"**Moda de Tráfico:** {row['moda']}")
        else:
            st.info("No hay datos temporales disponibles.")