import streamlit as st
import pandas as pd
import plotly.express as px
from s3_utils import load_from_s3


def render_quality_section():
    """Renderiza análisis de calidad: Bronze (original) y Silver (limpio)."""
    
    st.header("📊 Fase 1: Análisis Bronze (CSV Original)")
    df_bronze = load_from_s3("metadata/healthcheck_report/")

    if df_bronze is not None:
        total_f = df_bronze["total_filas_dataset"].iloc[0]
        total_d = df_bronze["duplicados_dataset"].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Registros", f"{total_f:,}")
        col2.metric("Duplicados", f"{total_d:,}", delta_color="inverse")
        col3.metric("Calidad Inicial", f"{(1 - total_d/total_f)*100:.2f}%")

        st.divider()
        st.subheader("📋 Resumen de Columnas: Bronze")
        cols_to_show = ["columna", "tipo_dato", "nulos_n", "nulos_pct", "unicos_n", "outliers_n"]
        st.dataframe(df_bronze[cols_to_show], use_container_width=True)

        c1, c2 = st.columns([0.6, 0.4])
        with c1:
            st.subheader("📉 % de Nulidad por Campo (Bronze)")
            df_sorted = df_bronze.sort_values("nulos_pct", ascending=True)
            h = len(df_sorted) * 25
            fig = px.bar(df_sorted, x="nulos_pct", y="columna", orientation='h',
                         color="nulos_pct", color_continuous_scale="Reds", height=h)
            fig.update_layout(margin=dict(l=150), yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("🚨 Distribución de Outliers")
            df_out = df_bronze[df_bronze["outliers_n"] > 0]
            if not df_out.empty:
                fig_out = px.pie(df_out, values="outliers_n", names="columna", hole=0.4,
                                color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_out, use_container_width=True)
            else:
                st.write("No se detectaron outliers.")

    st.write("---")
    st.header("✨ Fase 2: Análisis Silver (Parquet Limpio)")
    df_silver = load_from_s3("metadata/healthcheck_silver_parquet/")

    if df_silver is not None:
        total_s = df_silver["total_filas_dataset"].iloc[0]
        s1, s2, s3 = st.columns(3)
        s1.metric("Registros Únicos", f"{total_s:,}")
        s2.metric("Duplicados", "0", delta="Limpio", delta_color="normal")
        
        if df_bronze is not None:
            total_f = df_bronze["total_filas_dataset"].iloc[0]
            s3.metric("Reducción", f"{((total_f - total_s)/total_f)*100:.1f}%")

        st.divider()
        st.subheader("📋 Resumen de Columnas: Silver")
        st.dataframe(df_silver[["columna", "tipo_dato", "nulos_n", "nulos_pct", "unicos_n"]], 
                     use_container_width=True)

        sc1, sc2 = st.columns([0.6, 0.4])
        with sc1:
            st.subheader("📉 % de Nulidad por Campo (Silver)")
            df_s_sorted = df_silver.sort_values("nulos_pct", ascending=True)
            h = len(df_s_sorted) * 25
            fig_s = px.bar(df_s_sorted, x="nulos_pct", y="columna", orientation='h',
                           color="nulos_pct", color_continuous_scale="Blues", height=h)
            fig_s.update_layout(margin=dict(l=150), yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_s, use_container_width=True)
            
        with sc2:
            st.info("💡 En esta etapa los duplicados son 0.")
    else:
        st.warning("Reporte Silver no encontrado.")
