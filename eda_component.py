import streamlit as st
import plotly.express as px
import pandas as pd

EXPECTED_COLUMNS = {
    "geo": ["columna", "minimo", "maximo", "media"],
    "cats": ["columna", "moda"],
    "time": ["columna", "minimo", "maximo", "moda"]
}


def validate_columns(df, expected, section_name):
    missing = [col for col in expected if col not in df.columns]
    if missing:
        st.error(
            f"El reporte EDA para {section_name} no contiene las columnas esperadas: {missing}."
        )
        st.write("Columnas disponibles:", list(df.columns))
        return False
    return True


def render_eda_section(df_eda):
    st.header("📊 Análisis Estadístico de Negocio (NYC 311)")
    
    if df_eda is None or df_eda.empty:
        st.warning("No se encontraron datos en el reporte EDA.")
        return

    # Normalización defensiva de columnas para evitar KeyErrors
    df_eda.columns = [c.strip().lower().replace(" ", "_") for c in df_eda.columns]

    if "columna" not in df_eda.columns:
        st.error("El reporte EDA no contiene la columna esperada 'columna'.")
        st.write("Columnas disponibles:", list(df_eda.columns))
        return

    # Separamos la información por utilidad de negocio
    tab_cats, tab_geo, tab_time = st.tabs(["🏷️ Categorías Principales", "📍 Ubicación (NYC)", "📅 Tiempos"])

    with tab_cats:
        st.subheader("Modas y Frecuencias")
        st.write("¿Cuáles son los valores más recurrentes en los reportes?")
        if validate_columns(df_eda, EXPECTED_COLUMNS["cats"], "categorías"):
            df_c = df_eda[~df_eda["columna"].str.lower().str.contains("latitude|longitude|date")]
            if not df_c.empty:
                st.table(df_c[["columna", "moda"]])
            else:
                st.info("No hay datos categóricos disponibles.")

    with tab_geo:
        st.subheader("Límites de Cobertura Geográfica")
        df_g = df_eda[df_eda["columna"].str.lower().str.contains("latitude|longitude")]
        if not df_g.empty:
            if validate_columns(df_g, EXPECTED_COLUMNS["geo"], "geográfica"):
                st.dataframe(df_g[["columna", "minimo", "maximo", "media"]], use_container_width=True)
                st.caption("Nota: La latitud en NYC debe estar rondando los 40.7 y la longitud los -73.9.")
        else:
            st.info("No hay datos geográficos disponibles.")

    with tab_time:
        st.subheader("Ventana Temporal del Dataset")
        df_t = df_eda[df_eda["columna"].str.lower().str.contains("date")]
        if not df_t.empty:
            if validate_columns(df_t, EXPECTED_COLUMNS["time"], "temporal"):
                for _, row in df_t.iterrows():
                    # Presentación tipo "Card" para fechas
                    with st.expander(f"Periodo de: {row['columna'].upper()}"):
                        col1, col2 = st.columns(2)
                        col1.metric("Fecha Inicio", str(row["minimo"])[:10])
                        col2.metric("Fecha Fin", str(row["maximo"])[:10])
                        st.write(f"**Día/Hora con más reportes (Moda):** {row['moda']}")
        else:
            st.info("No hay datos temporales disponibles.")

def render_visual_charts(df):
    st.header("📈 Análisis Visual de Reportes (NYC 311)")
    
    # Limpieza rápida de fechas para las gráficas
    df['created date'] = pd.to_datetime(df['created date'])

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Top 10 Quejas")
        # AGREGACIÓN: Contamos los 210k registros y solo enviamos 10 al gráfico
        top_complaints = df['complaint type'].value_counts().head(10).reset_index()
        top_complaints.columns = ['Tipo', 'Cantidad']
        
        fig_bar = px.bar(top_complaints, x='Cantidad', y='Tipo', orientation='h',
                         color='Cantidad', color_continuous_scale='Reds')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        st.subheader("Distribución por Distrito (Borough)")
        # Pie Chart para variables con pocas categorías
        borough_dist = df['borough'].value_counts().reset_index()
        borough_dist.columns = ['Distrito', 'Total']
        
        fig_pie = px.pie(borough_dist, values='Total', names='Distrito', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    st.subheader("Evolución Temporal de Incidentes")
    # AGREGACIÓN: Agrupamos por día para que el gráfico de líneas sea fluido
    df_daily = df.groupby(df['created date'].dt.date).size().reset_index(name='Total')
    
    fig_line = px.line(df_daily, x='created date', y='Total', 
                       labels={'created date': 'Fecha', 'Total': 'Número de Quejas'},
                       title="Tendencia Diaria de Reportes")
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    st.subheader("📍 Mapa de Calor (Muestra Representativa)")
    # MUESTREO: Tomamos 5,000 puntos para que el mapa cargue en 1 segundo
    df_map_sample = df.dropna(subset=['latitude', 'longitude']).sample(n=min(5000, len(df)))
    
    fig_map = px.scatter_mapbox(df_map_sample, lat="latitude", lon="longitude", 
                                color="borough", hover_name="complaint type",
                                zoom=10, height=600, mapbox_style="carto-positron")
    st.plotly_chart(fig_map, use_container_width=True)