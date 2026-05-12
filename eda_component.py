import streamlit as st
import pandas as pd

def render_eda_section(df_eda):
    st.header("📊 Análisis de Valor de Negocio (NYC 311)")
    st.markdown("Estadísticas clave para la toma de decisiones basadas en los reportes.")

    if df_eda is None:
        st.error("No se pudo cargar el reporte EDA.")
        return

    # Dividimos la vista en el valor real de los datos
    t_frec, t_geo, t_time = st.tabs(["🔥 Top Incidentes (Modas)", "📍 Cobertura Geográfica", "📅 Rango Temporal"])

    with t_frec:
        st.subheader("Valores más frecuentes por Categoría")
        # Mostramos qué es lo que más se repite (Agency, Complaint Type, etc.)
        df_cat = df_eda[df_eda["tipo"].str.contains("String")]
        for _, row in df_cat.iterrows():
            st.write(f"**{row['columna']}**")
            st.info(f"El valor predominante es:  \n**{row['moda']}**")

    with t_geo:
        st.subheader("Límites Geográficos")
        df_geo = df_eda[df_eda["columna"].isin(["latitude", "longitude"])]
        if not df_geo.empty:
            st.table(df_geo[["columna", "minimo", "maximo", "media"]])
            st.caption("Estos valores definen el área de Nueva York cubierta por los datos.")

    with t_time:
        st.subheader("Periodo de los Datos")
        df_t = df_eda[df_eda["tipo"].str.contains("Timestamp")]
        for _, row in df_t.iterrows():
            c1, c2 = st.columns(2)
            c1.metric(f"Inicio {row['columna']}", row["minimo"][:10])
            c2.metric(f"Fin {row['columna']}", row["maximo"][:10])