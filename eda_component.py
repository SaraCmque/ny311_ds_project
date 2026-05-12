import streamlit as st
import plotly.express as px

def render_eda_section(df_eda):
    st.header("📈 Fase 3: Análisis Estadístico Profundo (EDA)")
    
    # 1. Filtros rápidos para el usuario
    tipos_disponibles = df_eda["tipo"].unique()
    filtro_tipo = st.multiselect("Filtrar métricas por tipo de dato:", tipos_disponibles, default=tipos_disponibles)
    
    df_filtrado = df_eda[df_eda["tipo"].isin(filtro_tipo)]

    # 2. Tabs internas para organizar las métricas
    t_num, t_cat, t_date = st.tabs(["🔢 Numéricos", "🔤 Categóricos", "📅 Temporales"])

    with t_num:
        st.subheader("Estadísticas de Tendencia Central")
        # Mostramos columnas que tienen media calculada (no es "N/A")
        df_num = df_filtrado[df_filtrado["media"] != "N/A"]
        if not df_num.empty:
            st.dataframe(df_num[["columna", "min_o_min_len", "max_o_max_len", "moda", "media", "desviacion"]], use_container_width=True)
            
            # Gráfico de barras para comparar medias
            df_num["media"] = df_num["media"].astype(float)
            fig_media = px.bar(df_num, x="columna", y="media", title="Comparativa de Medias Numéricas", color="media")
            st.plotly_chart(fig_media, use_container_width=True)
        else:
            st.info("No hay columnas numéricas seleccionadas.")

    with t_cat:
        st.subheader("Análisis de Textos y Categorías")
        # Filtramos por StringType
        df_cat = df_filtrado[df_filtrado["tipo"].str.contains("String", na=False)]
        if not df_cat.empty:
            st.write("Métricas de longitud de texto y valores más frecuentes (Moda):")
            st.dataframe(df_cat[["columna", "moda", "min_o_min_len", "max_o_max_len"]], use_container_width=True)
        else:
            st.info("No hay columnas de texto seleccionadas.")

    with t_date:
        st.subheader("Rango Temporal de los Datos")
        df_time = df_filtrado[df_filtrado["tipo"].str.contains("Timestamp", na=False)]
        if not df_time.empty:
            # Crear "cards" para cada fecha
            for _, row in df_time.iterrows():
                with st.expander(f"📅 {row['columna']}"):
                    c1, c2 = st.columns(2)
                    c1.metric("Fecha Inicio", row["min_o_min_len"][:10])
                    c2.metric("Fecha Fin", row["max_o_max_len"][:10])
                    st.write(f"**Valor más frecuente:** {row['moda']}")
        else:
            st.info("No hay columnas de fecha seleccionadas.")