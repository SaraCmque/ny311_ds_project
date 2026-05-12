import streamlit as st
import pandas as pd

def render_eda_section(df_eda):
    st.header("📊 Análisis Estadístico de Negocio (NYC 311)")
    
    if df_eda is None or df_eda.empty:
        st.warning("No se encontraron datos en el reporte EDA.")
        return

    # Normalización defensiva de columnas para evitar KeyErrors
    df_eda.columns = [c.strip().lower() for c in df_eda.columns]

    # Separamos la información por utilidad de negocio
    tab_cats, tab_geo, tab_time = st.tabs(["🏷️ Categorías Principales", "📍 Ubicación (NYC)", "📅 Tiempos"])

    with tab_cats:
        st.subheader("Modas y Frecuencias")
        st.write("¿Cuáles son los valores más recurrentes en los reportes?")
        # Filtramos las que no son coordenadas ni fechas
        df_c = df_eda[~df_eda["columna"].str.lower().str.contains("latitude|longitude|date")]
        if not df_c.empty:
            # Solo mostramos columnas útiles para el usuario final
            st.table(df_c[["columna", "moda"]])
        else:
            st.info("No hay datos categóricos disponibles.")

    with tab_geo:
        st.subheader("Límites de Cobertura Geográfica")
        # Aquí sí tiene sentido el min/max para ver si hay puntos fuera de New York
        df_g = df_eda[df_eda["columna"].str.lower().str.contains("latitude|longitude")]
        if not df_g.empty:
            # Usamos dataframe para que se vea limpio
            st.dataframe(df_g[["columna", "minimo", "maximo", "media"]], use_container_width=True)
            st.caption("Nota: La latitud en NYC debe estar rondando los 40.7 y la longitud los -73.9.")
        else:
            st.info("No hay datos geográficos disponibles.")

    with tab_time:
        st.subheader("Ventana Temporal del Dataset")
        df_t = df_eda[df_eda["columna"].str.lower().str.contains("date")]
        if not df_t.empty:
            for _, row in df_t.iterrows():
                # Presentación tipo "Card" para fechas
                with st.expander(f"Periodo de: {row['columna'].upper()}"):
                    col1, col2 = st.columns(2)
                    col1.metric("Fecha Inicio", str(row["minimo"])[:10])
                    col2.metric("Fecha Fin", str(row["maximo"])[:10])
                    st.write(f"**Día/Hora con más reportes (Moda):** {row['moda']}")
        else:
            st.info("No hay datos temporales disponibles.")