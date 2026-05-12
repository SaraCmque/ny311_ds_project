import streamlit as st
import pandas as pd
import plotly.express as px


def render_dynamic_charts(df: pd.DataFrame):
    """Renderiza gráficas dinámicas del dataset completo (Silver)."""
    
    st.header("📈 Análisis Visual de Reportes (NYC 311)")
    
    if df is None or df.empty:
        st.warning("No hay datos disponibles.")
        return
    
    df_work = df.copy()
    date_col = next((col for col in df_work.columns if 'created' in col.lower() and 'date' in col.lower()), None)
    complaint_col = next((col for col in df_work.columns if 'complaint' in col.lower() and 'type' in col.lower()), None)
    borough_col = next((col for col in df_work.columns if 'borough' in col.lower()), None)
    
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Top 10 Quejas")
        if complaint_col:
            top_complaints = df_work[complaint_col].value_counts().head(10).reset_index()
            top_complaints.columns = ['Tipo', 'Cantidad']
            fig = px.bar(top_complaints, x='Cantidad', y='Tipo', orientation='h',
                         color='Cantidad', color_continuous_scale='Reds')
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Distribución por Distrito")
        if borough_col:
            borough_dist = df_work[borough_col].value_counts().reset_index()
            borough_dist.columns = ['Distrito', 'Total']
            fig = px.pie(borough_dist, values='Total', names='Distrito', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    if date_col:
        st.subheader("Evolución Temporal de Incidentes")
        df_work[date_col] = pd.to_datetime(df_work[date_col], errors='coerce')
        df_daily = df_work.groupby(df_work[date_col].dt.date).size().reset_index()
        df_daily.columns = ['Fecha', 'Total']
        
        fig = px.line(df_daily, x='Fecha', y='Total',
                      title="Tendencia Diaria de Reportes")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    lat_col = next((col for col in df_work.columns if col.lower() == 'latitude'), None)
    lon_col = next((col for col in df_work.columns if col.lower() == 'longitude'), None)
    
    if lat_col and lon_col:
        st.subheader("📍 Mapa de Incidentes (Muestra)")
        df_map = df_work.dropna(subset=[lat_col, lon_col]).sample(n=min(5000, len(df_work)))
        
        fig = px.scatter_mapbox(df_map, lat=lat_col, lon=lon_col,
                                color=borough_col if borough_col else None,
                                hover_name=complaint_col if complaint_col else None,
                                zoom=10, height=600, mapbox_style="carto-positron")
        st.plotly_chart(fig, use_container_width=True)

