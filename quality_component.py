import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from s3_utils import load_from_s3

# ─────────────────────────────────────────────
# PALETA DE COLORES POR CAPA
# ─────────────────────────────────────────────
C_BRONZE  = "#CD7F32"
C_SILVER  = "#718096"
C_GOLD    = "#DAA520"
C_GOOD    = "#1E4D2B"
C_BAD     = "#C0292B"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def quality_score(df_meta: pd.DataFrame) -> float:
    if "nulos_pct" not in df_meta.columns:
        return 0.0
    return max(0.0, 100.0 - df_meta["nulos_pct"].mean())


def _bar_nullity(df_meta: pd.DataFrame, color_scale: str, title: str):
    df_s = df_meta.sort_values("nulos_pct", ascending=True)
    h = max(300, len(df_s) * 28)
    fig = px.bar(
        df_s, x="nulos_pct", y="columna", orientation="h",
        color="nulos_pct", color_continuous_scale=color_scale,
        labels={"nulos_pct": "% Nulos", "columna": "Campo"},
        title=title, height=h,
    )
    fig.update_layout(
        plot_bgcolor="white", margin=dict(l=160),
        yaxis={"categoryorder": "total ascending"},
        coloraxis_colorbar=dict(title="% Nulos"),
    )
    return fig


def _pie_dtype(df_meta: pd.DataFrame, title: str):
    counts = df_meta["tipo_dato"].value_counts().reset_index()
    counts.columns = ["tipo_dato", "cantidad"]
    fig = px.pie(
        counts, values="cantidad", names="tipo_dato", hole=0.45,
        title=title, color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textinfo="percent+label")
    return fig


def _gauge_quality(score: float, title: str, bar_color: str):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": title, "font": {"size": 15}},
        number={"suffix": "%", "font": {"size": 28}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": bar_color},
            "steps": [
                {"range": [0,   50], "color": "#FED7D7"},
                {"range": [50,  80], "color": "#FEFCBF"},
                {"range": [80, 100], "color": "#C6F6D5"},
            ],
            "threshold": {"line": {"color": C_BAD, "width": 3}, "thickness": 0.75, "value": 80},
        },
    ))
    fig.update_layout(height=250, margin=dict(t=40, b=20, l=20, r=20))
    return fig


def _corr_heatmap(df_data: pd.DataFrame, title: str):
    numeric = df_data.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return None
    if numeric.shape[1] > 25:
        numeric = numeric.iloc[:, :25]
    corr = numeric.corr()
    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.columns.tolist(),
        colorscale="RdBu", zmid=0, zmin=-1, zmax=1,
        colorbar=dict(title="Corr"),
        text=np.round(corr.values, 2),
        texttemplate="%{text}",
        hoverongaps=False,
    ))
    n = len(corr.columns)
    size = max(450, n * 55)
    fig.update_layout(
        title=title, height=size, width=size,
        xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=120, b=120),
    )
    return fig


def _outlier_bar(df_meta: pd.DataFrame, title: str):
    if "outliers_n" not in df_meta.columns:
        return None
    df_out = df_meta[df_meta["outliers_n"] > 0]
    if df_out.empty:
        return None
    fig = px.bar(
        df_out.sort_values("outliers_n", ascending=False),
        x="columna", y="outliers_n",
        color="outliers_n", color_continuous_scale="Oranges",
        title=title, labels={"outliers_n": "Outliers", "columna": "Campo"},
    )
    fig.update_layout(plot_bgcolor="white", xaxis_tickangle=-30)
    return fig


def _uniques_bar(df_meta: pd.DataFrame, title: str, bar_color: str):
    fig = px.bar(
        df_meta.sort_values("unicos_n", ascending=False),
        x="columna", y="unicos_n",
        color_discrete_sequence=[bar_color],
        title=title, labels={"unicos_n": "Valores únicos", "columna": "Campo"},
    )
    fig.update_layout(plot_bgcolor="white", xaxis_tickangle=-30)
    return fig


# ─────────────────────────────────────────────
# SECCIÓN BRONZE
# ─────────────────────────────────────────────
def _render_bronze(df_bronze: pd.DataFrame):
    st.markdown(f"## 🟤 Capa Bronze — CSV Original")

    total_f = df_bronze["total_filas_dataset"].iloc[0]
    total_d = df_bronze["duplicados_dataset"].iloc[0]
    score   = quality_score(df_bronze)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Registros",    f"{total_f:,}")
    c2.metric("Duplicados",          f"{total_d:,}",  delta_color="inverse")
    c3.metric("Campos en el schema", f"{len(df_bronze):,}")
    c4.metric("Score de Calidad",    f"{score:.1f}%")

    st.divider()

    cols_show = [c for c in ["columna","tipo_dato","nulos_n","nulos_pct","unicos_n","outliers_n"] if c in df_bronze.columns]
    st.subheader("📋 Resumen de Columnas")
    st.dataframe(df_bronze[cols_show].style.background_gradient(subset=["nulos_pct"], cmap="Reds"), use_container_width=True)

    st.divider()

    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(_gauge_quality(score, "Score Calidad Bronze", C_BRONZE), use_container_width=True)
    with g2:
        st.plotly_chart(_pie_dtype(df_bronze, "Distribución de Tipos de Dato"), use_container_width=True)

    st.divider()
    st.subheader("📊 % de Nulidad por Campo")
    st.plotly_chart(_bar_nullity(df_bronze, "Reds", "Nulidad por Campo — Bronze"), use_container_width=True)

    st.divider()
    o1, o2 = st.columns(2)
    with o1:
        fig_out = _outlier_bar(df_bronze, "Campos con Outliers — Bronze")
        if fig_out:
            st.plotly_chart(fig_out, use_container_width=True)
        else:
            st.info("No se detectaron outliers en Bronze.")
    with o2:
        st.plotly_chart(_uniques_bar(df_bronze, "Cardinalidad por Campo — Bronze", C_BRONZE), use_container_width=True)


# ─────────────────────────────────────────────
# SECCIÓN SILVER
# ─────────────────────────────────────────────
def _render_silver(df_silver: pd.DataFrame, df_bronze):
    st.markdown("## 🔘 Capa Silver — Parquet Limpio")

    total_s = df_silver["total_filas_dataset"].iloc[0]
    score_s = quality_score(df_silver)

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Registros Únicos",   f"{total_s:,}")
    sc2.metric("Duplicados",          "0",  delta="Eliminados ✔", delta_color="normal")
    sc3.metric("Campos en el schema", f"{len(df_silver):,}")
    sc4.metric("Score de Calidad",    f"{score_s:.1f}%")

    if df_bronze is not None:
        total_f = df_bronze["total_filas_dataset"].iloc[0]
        st.caption(f"ℹ️ Reducción del {((total_f - total_s)/total_f)*100:.1f}% del volumen respecto a Bronze.")

    st.divider()

    cols_show = [c for c in ["columna","tipo_dato","nulos_n","nulos_pct","unicos_n"] if c in df_silver.columns]
    st.subheader("📋 Resumen de Columnas")
    st.dataframe(df_silver[cols_show].style.background_gradient(subset=["nulos_pct"], cmap="Blues"), use_container_width=True)

    st.divider()

    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(_gauge_quality(score_s, "Score Calidad Silver", C_SILVER), use_container_width=True)
    with g2:
        st.plotly_chart(_pie_dtype(df_silver, "Distribución de Tipos de Dato"), use_container_width=True)

    st.divider()
    st.subheader("📊 % de Nulidad por Campo")
    st.plotly_chart(_bar_nullity(df_silver, "Blues", "Nulidad por Campo — Silver"), use_container_width=True)

    st.divider()
    st.plotly_chart(_uniques_bar(df_silver, "Cardinalidad por Campo — Silver", C_SILVER), use_container_width=True)


# ─────────────────────────────────────────────
# SECCIÓN GOLD
# ─────────────────────────────────────────────
def _render_gold(df_gold: pd.DataFrame):
    st.markdown("## 🥇 Capa Gold — Feature Enrichment")

    total_g  = len(df_gold)
    num_cols = df_gold.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df_gold.select_dtypes(exclude=[np.number]).columns.tolist()
    null_pct = df_gold.isnull().mean().mean() * 100

    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Registros",          f"{total_g:,}")
    g2.metric("Campos Numéricos",    f"{len(num_cols):,}")
    g3.metric("Campos Categóricos",  f"{len(cat_cols):,}")
    g4.metric("Nulidad Promedio",    f"{null_pct:.2f}%")

    st.divider()

    # Nulidad real sobre datos Gold
    st.subheader("📊 Nulidad por Campo — Gold")
    nulls = df_gold.isnull().mean().reset_index()
    nulls.columns = ["columna", "nulos_pct"]
    nulls["nulos_pct"] = (nulls["nulos_pct"] * 100).round(2)
    nulls_s = nulls.sort_values("nulos_pct", ascending=True)
    h = max(300, len(nulls_s) * 20)
    fig_n = px.bar(
        nulls_s, x="nulos_pct", y="columna", orientation="h",
        color="nulos_pct", color_continuous_scale="YlOrBr",
        height=h, title="% Nulos — Gold",
        labels={"nulos_pct": "% Nulos", "columna": "Campo"},
    )
    fig_n.update_layout(plot_bgcolor="white", margin=dict(l=220), yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_n, use_container_width=True)

    st.divider()

    # Tipos de dato + gauge
    dtype_df = pd.DataFrame({"tipo": df_gold.dtypes.astype(str)}).reset_index()
    dtype_df.columns = ["columna", "tipo"]
    cnt = dtype_df["tipo"].value_counts().reset_index()
    cnt.columns = ["tipo", "cantidad"]
    fig_dt = px.pie(cnt, values="cantidad", names="tipo", hole=0.45,
                    title="Distribución de Tipos de Dato — Gold",
                    color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_dt.update_traces(textinfo="percent+label")

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(fig_dt, use_container_width=True)
    with col_b:
        score_g = max(0.0, 100.0 - null_pct)
        st.plotly_chart(_gauge_quality(score_g, "Score Calidad Gold", C_GOLD), use_container_width=True)

    st.divider()

    if num_cols:
        st.subheader("📈 Estadísticas Descriptivas — Campos Numéricos")
        st.dataframe(df_gold[num_cols].describe().T.style.background_gradient(cmap="YlOrBr"), use_container_width=True)

    st.divider()

    st.subheader("🔗 Matriz de Correlación — Gold")
    fig_corr = _corr_heatmap(df_gold, "Correlación entre Variables Numéricas — Gold")
    if fig_corr:
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("No hay suficientes columnas numéricas para calcular correlación en Gold.")


# ─────────────────────────────────────────────
# CORRELACIONES METADATA Bronze / Silver
# ─────────────────────────────────────────────
def _render_corr_metadata(df_bronze, df_silver):
    st.markdown("### 🔗 Correlación de Métricas de Calidad por Campo")
    st.caption("Muestra cómo se relacionan las métricas de calidad (nulos, cardinalidad, outliers) dentro de cada capa.")
    numeric_meta_cols = ["nulos_n", "nulos_pct", "unicos_n", "outliers_n"]

    tab_b, tab_s = st.tabs(["🟤 Bronze", "🔘 Silver"])

    with tab_b:
        if df_bronze is not None:
            avail = [c for c in numeric_meta_cols if c in df_bronze.columns]
            if len(avail) >= 2:
                fig = _corr_heatmap(df_bronze[avail], "Correlación de Métricas de Calidad — Bronze")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Columnas numéricas insuficientes en metadata Bronze.")
        else:
            st.warning("Metadata Bronze no disponible.")

    with tab_s:
        if df_silver is not None:
            avail = [c for c in numeric_meta_cols if c in df_silver.columns]
            if len(avail) >= 2:
                fig = _corr_heatmap(df_silver[avail], "Correlación de Métricas de Calidad — Silver")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Columnas numéricas insuficientes en metadata Silver.")
        else:
            st.warning("Metadata Silver no disponible.")


# ─────────────────────────────────────────────
# CORRELACIÓN INTERACTIVA GOLD (datos reales)
# ─────────────────────────────────────────────
def _render_real_corr(df_gold: pd.DataFrame):
    st.subheader("🔗 Correlación en Datos Reales — Gold")
    num_cols = df_gold.select_dtypes(include=[np.number]).columns.tolist()
    if len(num_cols) < 2:
        st.info("No hay suficientes columnas numéricas en Gold.")
        return

    selected = st.multiselect(
        "Selecciona campos para la matriz de correlación (mín. 2):",
        options=num_cols,
        default=num_cols[:min(12, len(num_cols))],
        key="corr_gold_select",
    )

    if len(selected) < 2:
        st.warning("Selecciona al menos 2 campos.")
        return

    fig = _corr_heatmap(df_gold[selected], "Matriz de Correlación — Campos Seleccionados (Gold)")
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    st.caption("💡 Valores > 0.7 (azul) = correlación positiva fuerte; < -0.7 (rojo) = negativa fuerte.")


# ─────────────────────────────────────────────
# COMPARATIVA INTERACTIVA Bronze vs Silver
# ─────────────────────────────────────────────
def _render_comparison(df_bronze: pd.DataFrame, df_silver: pd.DataFrame):
    st.markdown("## ⚖️ Comparativa Interactiva: Bronze vs Silver")
    st.caption("Selecciona campos y métricas para ver cómo mejoró la calidad tras la limpieza Silver.")

    bronze_cols = set(df_bronze["columna"].tolist())
    silver_cols = set(df_silver["columna"].tolist())
    common_cols = sorted(bronze_cols & silver_cols)

    score_b = quality_score(df_bronze)
    score_s = quality_score(df_silver)

    sb1, sb2, sb3 = st.columns(3)
    sb1.metric("Score Bronze",   f"{score_b:.1f}%")
    sb2.metric("Score Silver",   f"{score_s:.1f}%", delta=f"+{score_s - score_b:.1f}%", delta_color="normal")
    sb3.metric("Campos comunes", f"{len(common_cols)}")

    st.divider()

    metric_options = {
        "% Nulidad (nulos_pct)":     "nulos_pct",
        "N° Nulos (nulos_n)":        "nulos_n",
        "Valores Únicos (unicos_n)": "unicos_n",
    }
    if "outliers_n" in df_bronze.columns:
        metric_options["N° Outliers (outliers_n)"] = "outliers_n"

    col_ctrl1, col_ctrl2 = st.columns([1, 2])
    with col_ctrl1:
        metric_label = st.selectbox("Métrica a comparar:", list(metric_options.keys()))
        metric       = metric_options[metric_label]
        chart_type   = st.radio("Tipo de gráfica:", ["Barras agrupadas", "Barras apiladas", "Scatter"], horizontal=True)
    with col_ctrl2:
        selected_cols = st.multiselect(
            "Filtrar campos (vacío = todos los comunes):",
            options=common_cols, default=[],
        )

    use_cols = selected_cols if selected_cols else common_cols
    color_map = {"Bronze": C_BRONZE, "Silver": C_SILVER}

    df_b_filt = df_bronze[df_bronze["columna"].isin(use_cols)][["columna", metric]].copy()
    df_b_filt["capa"] = "Bronze"
    df_s_filt = df_silver[df_silver["columna"].isin(use_cols)][["columna", metric]].copy()
    df_s_filt["capa"] = "Silver"
    df_comp = pd.concat([df_b_filt, df_s_filt], ignore_index=True).dropna(subset=[metric])

    if chart_type == "Barras agrupadas":
        fig = px.bar(df_comp, x="columna", y=metric, color="capa", barmode="group",
                     color_discrete_map=color_map,
                     title=f"{metric_label} — Bronze vs Silver",
                     labels={"columna": "Campo", metric: metric_label, "capa": "Capa"})
    elif chart_type == "Barras apiladas":
        fig = px.bar(df_comp, x="columna", y=metric, color="capa", barmode="stack",
                     color_discrete_map=color_map,
                     title=f"{metric_label} — Bronze vs Silver (apilado)",
                     labels={"columna": "Campo", metric: metric_label, "capa": "Capa"})
    else:
        df_pivot = df_comp.pivot(index="columna", columns="capa", values=metric).reset_index().dropna()
        if "Bronze" in df_pivot.columns and "Silver" in df_pivot.columns:
            fig = px.scatter(df_pivot, x="Bronze", y="Silver", text="columna",
                             title=f"{metric_label}: Bronze (X) vs Silver (Y)",
                             labels={"Bronze": f"Bronze — {metric_label}", "Silver": f"Silver — {metric_label}"},
                             color_discrete_sequence=[C_BRONZE])
            max_val = max(df_pivot["Bronze"].max(), df_pivot["Silver"].max())
            fig.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val], mode="lines",
                                     name="Sin cambio", line=dict(dash="dash", color=C_BAD)))
            fig.update_traces(textposition="top center", selector=dict(mode="markers+text"))
        else:
            fig = go.Figure()
            fig.add_annotation(text="No hay campos comunes suficientes.", xref="paper", yref="paper", x=0.5, y=0.5)

    fig.update_layout(plot_bgcolor="white", xaxis_tickangle=-40)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Top campos con mayor mejora de nulidad
    st.subheader("🏆 Campos con Mayor Mejora (reducción de nulos)")
    if "nulos_pct" in df_bronze.columns and "nulos_pct" in df_silver.columns:
        df_b_n = df_bronze[df_bronze["columna"].isin(common_cols)][["columna", "nulos_pct"]].rename(columns={"nulos_pct": "bronze_pct"})
        df_s_n = df_silver[df_silver["columna"].isin(common_cols)][["columna", "nulos_pct"]].rename(columns={"nulos_pct": "silver_pct"})
        df_mej = df_b_n.merge(df_s_n, on="columna")
        df_mej["mejora"] = df_mej["bronze_pct"] - df_mej["silver_pct"]
        df_mej = df_mej.sort_values("mejora", ascending=False).head(20)

        fig_mej = go.Figure()
        fig_mej.add_trace(go.Bar(x=df_mej["columna"], y=df_mej["bronze_pct"],
                                  name="Bronze", marker_color=C_BRONZE, opacity=0.85))
        fig_mej.add_trace(go.Bar(x=df_mej["columna"], y=df_mej["silver_pct"],
                                  name="Silver", marker_color=C_SILVER, opacity=0.9))
        fig_mej.update_layout(
            barmode="group", plot_bgcolor="white",
            title="Top 20 Campos: Nulidad Bronze vs Silver",
            xaxis_tickangle=-35, yaxis_title="% Nulos",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_mej, use_container_width=True)

    st.divider()

    # Scoreboard
    st.subheader("📊 Scoreboard Completo por Campo")
    if "nulos_pct" in df_bronze.columns and "nulos_pct" in df_silver.columns:
        sb_b = df_bronze[["columna", "nulos_pct", "unicos_n"]].add_suffix("_b").rename(columns={"columna_b": "columna"})
        sb_s = df_silver[["columna", "nulos_pct", "unicos_n"]].add_suffix("_s").rename(columns={"columna_s": "columna"})
        sb   = sb_b.merge(sb_s, on="columna", how="inner")
        sb["Δ nulos_pct"] = (sb["nulos_pct_s"] - sb["nulos_pct_b"]).round(2)
        sb["estado"] = sb["Δ nulos_pct"].apply(lambda x: "✅ Mejoró" if x < 0 else ("➡️ Igual" if x == 0 else "⚠️ Empeoró"))
        sb = sb.rename(columns={
            "nulos_pct_b": "Nulos% Bronze", "nulos_pct_s": "Nulos% Silver",
            "unicos_n_b": "Únicos Bronze",  "unicos_n_s": "Únicos Silver",
        })
        st.dataframe(
            sb[["columna", "Nulos% Bronze", "Nulos% Silver", "Δ nulos_pct", "Únicos Bronze", "Únicos Silver", "estado"]]
            .sort_values("Δ nulos_pct"),
            use_container_width=True,
        )


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA PRINCIPAL
# ─────────────────────────────────────────────
def render_quality_section():
    """Renderiza el tab completo de Control de Calidad — Arquitectura Medallion."""

    with st.spinner("Cargando reportes de calidad…"):
        df_bronze = load_from_s3("metadata/healthcheck_report/")
        df_silver = load_from_s3("metadata/healthcheck_silver_parquet/")
        df_gold   = load_from_s3("gold/enhanced_for_streamlit_eda/")

    st.title("🔍 Control de Calidad — Arquitectura Medallion")
    st.markdown(
        "Análisis de calidad de datos en cada capa: **Bronze** (raw CSV), "
        "**Silver** (Parquet limpio) y **Gold** (Feature-enriched). "
        "Incluye métricas, gráficas, matrices de correlación y comparativa interactiva Bronze ↔ Silver."
    )

    # Gauges globales lado a lado
    if df_bronze is not None or df_silver is not None or df_gold is not None:
        k1, k2, k3 = st.columns(3)
        with k1:
            score_b = quality_score(df_bronze) if df_bronze is not None else 0.0
            st.plotly_chart(_gauge_quality(score_b, "🟤 Bronze", C_BRONZE), use_container_width=True)
        with k2:
            score_s = quality_score(df_silver) if df_silver is not None else 0.0
            st.plotly_chart(_gauge_quality(score_s, "🔘 Silver", C_SILVER), use_container_width=True)
        with k3:
            score_g = (100.0 - df_gold.isnull().mean().mean() * 100) if df_gold is not None else 0.0
            st.plotly_chart(_gauge_quality(score_g, "🥇 Gold",   C_GOLD),   use_container_width=True)

    st.divider()

    tab_bronze, tab_silver, tab_gold, tab_comp, tab_corr = st.tabs([
        "🟤 Bronze",
        "🔘 Silver",
        "🥇 Gold",
        "⚖️ Bronze vs Silver",
        "🔗 Correlaciones",
    ])

    with tab_bronze:
        if df_bronze is not None:
            _render_bronze(df_bronze)
        else:
            st.error("No se encontró el reporte Bronze en S3.")

    with tab_silver:
        if df_silver is not None:
            _render_silver(df_silver, df_bronze)
        else:
            st.error("No se encontró el reporte Silver en S3.")

    with tab_gold:
        if df_gold is not None:
            _render_gold(df_gold)
        else:
            st.error("No se encontraron datos Gold en S3.")

    with tab_comp:
        if df_bronze is not None and df_silver is not None:
            _render_comparison(df_bronze, df_silver)
        else:
            st.warning("Se necesitan ambos reportes (Bronze y Silver) para la comparativa.")

    with tab_corr:
        st.markdown("## 🔗 Matrices de Correlación por Capa")
        st.markdown(
            "Para **Bronze** y **Silver** se correlacionan las *métricas de calidad* de cada campo "
            "(nulos, cardinalidad, outliers). Para **Gold** se usa la correlación real entre campos numéricos."
        )
        st.divider()
        _render_corr_metadata(df_bronze, df_silver)
        st.divider()
        if df_gold is not None:
            _render_real_corr(df_gold)
        else:
            st.warning("Datos Gold no disponibles para correlación.")
