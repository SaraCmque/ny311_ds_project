import streamlit as st
import pandas as pd
import plotly.express as px


def render_dynamic_charts(df: pd.DataFrame):
    """Renderiza gráficas dinámicas optimizadas para la Ingeniería de la Atención."""
    
    st.header("Análisis Visual de Reportes (NYC 311)")
    
    if df is None or df.empty:
        st.warning("No hay datos disponibles.")
        return
    
    df_work = df.copy()
    date_col = next((col for col in df_work.columns if 'created' in col.lower() and 'date' in col.lower()), None)
    complaint_col = next((col for col in df_work.columns if 'complaint' in col.lower() and 'type' in col.lower()), None)
    borough_col = next((col for col in df_work.columns if 'borough' in col.lower()), None)
    
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
            
            # ORDENACIÓN: Total ascendente para que la barra más larga (HEAT/HOT WATER) quede arriba
            # COLOR SELECTIVO: Solo la barra superior es Roja, el resto Gris
            colores_quejas = [COLOR_NEUTRO] * len(top_complaints)
            colores_quejas[-1] = COLOR_FOCO  # La barra con más valor (última en el dataframe ordenado de forma ascendente)

            fig = px.bar(top_complaints, x='Cantidad', y='Tipo', orientation='h')
            
            fig.update_traces(marker_color=colores_quejas, marker_line_color=colores_quejas, opacity=0.85)
            fig.update_layout(
                yaxis={'categoryorder':'total ascending'},
                showlegend=False,
                plot_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(showgrid=False, title="Número de Reportes"),
                yaxis=dict(title="")
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Distribución por Distrito (Volumen de Carga)")
        if borough_col:
            borough_dist = df_work[borough_col].value_counts().reset_index()
            borough_dist.columns = ['Distrito', 'Total']
            
            # ORDENACIÓN: De mayor a menor volumen
            borough_dist = borough_dist.sort_values(by='Total', ascending=True)
            
            # COLOR SELECTIVO: Destacar BROOKLYN por encima de todos
            colores_distritos = [
                COLOR_FOCO if dist == "BROOKLYN" else COLOR_NEUTRO 
                for dist in borough_dist['Distrito']
            ]
            
            # REEMPLAZO DE LA TORA POR GRÁFICO DE BARRAS HORIZONTALES
            fig = px.bar(borough_dist, x='Total', y='Distrito', orientation='h')
            
            fig.update_traces(marker_color=colores_distritos, opacity=0.85)
            fig.update_layout(
                showlegend=False,
                plot_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(showgrid=False, title="Total de Reportes"),
                yaxis=dict(title="")
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    if date_col:
        st.subheader("Evolución Temporal de Incidentes")
        df_work[date_col] = pd.to_datetime(df_work[date_col], errors='coerce')
        df_daily = df_work.groupby(df_work[date_col].dt.date).size().reset_index()
        df_daily.columns = ['Fecha', 'Total']
        
        # REDUCCIÓN DE RUIDO: Línea limpia sin cuadrículas excesivas
        fig = px.line(df_daily, x='Fecha', y='Total')
        fig.update_traces(line_color=COLOR_NEUTRO, line_width=2)
        fig.update_layout(
            plot_bgcolor=COLOR_FONDO_LIGERO,
            xaxis=dict(showgrid=False, title="Línea de Tiempo"),
            yaxis=dict(showgrid=True, gridcolor="rgba(200,200,200,0.1)", title="Frecuencia Diaria")
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    lat_col = next((col for col in df_work.columns if col.lower() == 'latitude'), None)
    lon_col = next((col for col in df_work.columns if col.lower() == 'longitude'), None)
    
    if lat_col and lon_col:
        st.subheader("Concentración Geográfica de Incidentes")
        df_map = df_work.dropna(subset=[lat_col, lon_col]).sample(n=min(5000, len(df_work)))
        
        # COLOR SELECTIVO EN MAPA: Puntos en Brooklyn o de calor específicos reciben la atención
        # Usamos un mapa oscuro ("dark") o minimalista para que resalten los puntos
        fig = px.scatter_mapbox(df_map, lat=lat_col, lon=lon_col,
                                hover_name=complaint_col if complaint_col else None,
                                zoom=10, height=600, mapbox_style="carto-darkmatter")
        
        # Si el distrito es Brooklyn, lo pintamos rojo, si no, gris tenue
        if borough_col:
            colores_mapa = [COLOR_FOCO if b == "BROOKLYN" else "#718096" for b in df_map[borough_col]]
            fig.update_traces(marker=dict(color=colores_mapa, size=4, opacity=0.6))
            
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Nota: Muestra aleatoria de 5,000 registros para optimización de memoria.")

