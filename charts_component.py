import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_dynamic_charts(df: pd.DataFrame):
    """Renderiza gráficas dinámicas optimizadas para la Ingeniería de la Atención."""
    
    st.header("Análisis Visual de Reportes (NYC 311)")
    
    if df is None or df.empty:
        st.warning("No hay datos disponibles.")
        return
    
    df_work = df.copy()
    
    # Mapeo estricto de columnas sobre las 210k filas de la capa Silver
    date_col = next((col for col in df_work.columns if 'created' in col.lower() and 'date' in col.lower()), None)
    closed_col = next((col for col in df_work.columns if 'closed' in col.lower() and 'date' in col.lower()), None)
    complaint_col = next((col for col in df_work.columns if 'complaint' in col.lower() and 'type' in col.lower()), None)
    borough_col = next((col for col in df_work.columns if 'borough' in col.lower()), None)
    
    # Normalización de marcas de tiempo
    if date_col:
        df_work[date_col] = pd.to_datetime(df_work[date_col], errors='coerce')
    if closed_col:
        df_work[closed_col] = pd.to_datetime(df_work[closed_col], errors='coerce')
    
    col_a, col_b = st.columns(2)

    # PALETA DE COLORES SELECTIVA (Gris para control, Rojo para llamar la atención)
    COLOR_FOCO = "#D9383A"       # Rojo estratégico
    COLOR_NEUTRO = "#4A5568"     # Gris oscuro sutil para barras secundarias
    COLOR_FONDO_LIGERO = "rgba(0,0,0,0)"

    with col_a:
        st.subheader("Top 10 Quejas Principalmente Críticas")
        if complaint_col:
            top_complaints = df_work[complaint_col].value_counts().head(10).reset_index()
            top_complaints.columns = ['Tipo', 'Cantidad']
            
            colores_quejas = [COLOR_NEUTRO] * len(top_complaints)
            colores_quejas[-1] = COLOR_FOCO  # La barra con más valor
            
            fig = px.bar(top_complaints, x='Cantidad', y='Tipo', orientation='h')
            fig.update_traces(marker_color=colores_quejas, marker_line_color=colores_quejas, opacity=0.85)
            fig.update_layout(
                showlegend=False,
                plot_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(showgrid=False, title="Número de Reportes"),
                yaxis=dict(categoryorder='total ascending', title_text="")
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Distribución por Distrito (Volumen de Carga)")
        if borough_col:
            borough_dist = df_work[borough_col].value_counts().reset_index()
            borough_dist.columns = ['Distrito', 'Total']
            
            borough_dist = borough_dist.sort_values(by='Total', ascending=True)
            colores_distritos = [
                COLOR_FOCO if dist == "BROOKLYN" else COLOR_NEUTRO 
                for dist in borough_dist['Distrito']
            ]
            
            fig = px.bar(borough_dist, x='Total', y='Distrito', orientation='h')
            fig.update_traces(marker_color=colores_distritos, opacity=0.85)
            fig.update_layout(
                showlegend=False,
                plot_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(showgrid=False, title="Total de Reportes"),
                yaxis=dict(title_text="")
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    if date_col:
        st.subheader("Evolución Temporal de Incidentes")
        df_daily = df_work.groupby(df_work[date_col].dt.date).size().reset_index()
        df_daily.columns = ['Fecha', 'Total']
        
        idx_max = df_daily['Total'].idxmax()
        idx_min = df_daily['Total'].idxmin()
        row_max = df_daily.loc[idx_max]
        row_min = df_daily.loc[idx_min]

        fig = px.line(df_daily, x='Fecha', y='Total')
        fig.update_traces(line_color=COLOR_NEUTRO, line_width=2, name="Tendencia")
        
        # Pico Máximo (Rojo Estratégico)
        fig.add_trace(go.Scatter(
            x=[row_max['Fecha']], 
            y=[row_max['Total']],
            mode='markers+text',
            marker=dict(color=COLOR_FOCO, size=12, line=dict(width=2, color='white')),
            text=[f"Pico Máximo: {row_max['Total']}"],
            textposition="top center",
            textfont=dict(color="white", size=12),
            name="Máximo Histórico"
        ))
        
        # Punto Mínimo
        fig.add_trace(go.Scatter(
            x=[row_min['Fecha']], 
            y=[row_min['Total']],
            mode='markers+text',
            marker=dict(color="#63B3ED", size=10, line=dict(width=2, color='white')),
            text=[f"Mínimo: {row_min['Total']}"],
            textposition="bottom center",
            textfont=dict(color="#A0AEC0", size=11),
            name="Mínimo Histórico"
        ))
        
        fig.update_layout(
            showlegend=False,
            plot_bgcolor=COLOR_FONDO_LIGERO,
            xaxis=dict(showgrid=False, title="Línea de Tiempo"),
            yaxis=dict(showgrid=True, gridcolor="rgba(200,200,200,0.1)", title_text="Frecuencia Diaria")
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ======================================================================
    # NUEVA SECCIÓN: EFICIENCIA OPERATIVA (DETECCIÓN DE ANOMALÍAS EN SLAs)
    # ======================================================================
    st.subheader("⏳ Eficiencia y Cuellos de Botella en Respuesta (SLAs)")
    st.write("Análisis del tiempo promedio requerido para resolver y cerrar incidentes por categoría.")
    
    if date_col and closed_col and complaint_col:
        # Calcular delta de resolución en días para las 210k filas
        df_work['dias_resolucion'] = (df_work[closed_col] - df_work[date_col]).dt.total_seconds() / 86400
        df_sla = df_work[df_work['dias_resolucion'] >= 0].dropna(subset=['dias_resolucion'])
        
        if not df_sla.empty:
            # Agrupación por promedios de atención
            df_sla_avg = df_sla.groupby(complaint_col)['dias_resolucion'].mean().reset_index()
            df_sla_avg = df_sla_avg.sort_values(by='dias_resolucion', ascending=False).head(10)
            
            # Ordenar ascendente para la visualización en Plotly horizontal (peor tiempo arriba)
            df_sla_avg = df_sla_avg.sort_values(by='dias_resolucion', ascending=True)
            
            colores_sla = [COLOR_NEUTRO] * len(df_sla_avg)
            colores_sla[-1] = COLOR_FOCO  # Pintar de rojo la anomalía de retraso masivo (Top 1)
            
            fig_sla = px.bar(df_sla_avg, x='dias_resolucion', y=complaint_col, orientation='h')
            fig_sla.update_traces(marker_color=colores_sla, opacity=0.9)
            
            # Captura de datos de la peor categoría para la anotación inteligente
            peor_cat = df_sla_avg.iloc[-1][complaint_col]
            peor_dia = df_sla_avg.iloc[-1]['dias_resolucion']
            
            fig_sla.update_layout(
                plot_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(showgrid=True, gridcolor="rgba(100,100,100,0.1)", title="Días Promedio de Cierre"),
                yaxis=dict(title_text=""),
                # Evitar cortes: le damos aire a la derecha de la barra más larga
                xaxis_range=[0, peor_dia * 1.3],
                annotations=[
                    dict(
                        x=peor_dia,
                        y=peor_cat,
                        text=f"⚠️ <b>RETRASTO ANORMAL DETECTADO</b><br>La categoría <i>{peor_cat}</i> de la ciudad<br>rompe los SLAs con {peor_dia:.1f} días promedio.",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor=COLOR_FOCO,
                        ax=80,
                        ay=0,
                        font=dict(color=COLOR_FOCO, size=11),
                        bgcolor="rgba(255, 255, 255, 0.95)",
                        bordercolor=COLOR_FOCO,
                        borderwidth=1
                    )
                ]
            )
            st.plotly_chart(fig_sla, use_container_width=True)
        else:
            st.info("No hay suficientes registros con fechas de cierre válidas para procesar SLAs.")
            
    st.divider()

    # ======================================================================
    # CONTINUIDAD: CONCENTRACIÓN GEOGRÁFICA ORIGINAL
    # ======================================================================
    lat_col = next((col for col in df_work.columns if col.lower() == 'latitude'), None)
    lon_col = next((col for col in df_work.columns if col.lower() == 'longitude'), None)
    
    if lat_col and lon_col:
        st.subheader("Concentración Geográfica de Incidentes")
        df_map = df_work.dropna(subset=[lat_col, lon_col]).sample(n=min(5000, len(df_work)))
        
        fig = px.scatter_mapbox(df_map, lat=lat_col, lon=lon_col,
                                hover_name=complaint_col if complaint_col else None,
                                zoom=10, height=600, mapbox_style="carto-darkmatter")
        
        if borough_col:
            colores_mapa = [COLOR_FOCO if b == "BROOKLYN" else "#718096" for b in df_map[borough_col]]
            fig.update_traces(marker=dict(color=colores_mapa, size=4, opacity=0.6))
            
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Nota: Muestra aleatoria de 5,000 registros para optimización de memoria.")