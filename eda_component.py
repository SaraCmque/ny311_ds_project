import streamlit as st

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
    st.header("Análisis Estadístico de Negocio (NYC 311)")
    
    if df_eda is None or df_eda.empty:
        st.warning("No se encontraron datos en el reporte EDA.")
        return

    df_eda.columns = [c.strip().lower().replace(" ", "_") for c in df_eda.columns]

    if "columna" not in df_eda.columns:
        st.error("El reporte EDA no contiene la columna esperada 'columna'.")
        st.write("Columnas disponibles:", list(df_eda.columns))
        return

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
                st.caption("Latitud NYC ≈ 40.7 | Longitud NYC ≈ -73.9")
        else:
            st.info("No hay datos geográficos disponibles.")

    with tab_time:
        st.subheader("Ventana Temporal del Dataset")
        df_t = df_eda[df_eda["columna"].str.lower().str.contains("date")]
        if not df_t.empty:
            if validate_columns(df_t, EXPECTED_COLUMNS["time"], "temporal"):
                for _, row in df_t.iterrows():
                    with st.expander(f"Periodo de: {row['columna'].upper()}"):
                        col1, col2 = st.columns(2)
                        col1.metric("Fecha Inicio", str(row["minimo"])[:10])
                        col2.metric("Fecha Fin", str(row["maximo"])[:10])
                        st.write(f"**Moda:** {row['moda']}")
        else:
            st.info("No hay datos temporales disponibles.")
