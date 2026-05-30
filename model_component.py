"""
model_component.py
Visualización de resultados del modelo predictivo NY-311.
Carga los 7 parquets de s3://proyect-ny311/gold_v2/model_results/
y los presenta con el Vocabulario Visual del proyecto.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from s3_utils import load_parquet_from_s3

# ── Paleta ──────────────────────────────────────────────────────────────────
C_RED    = "#C0292B"
C_GREEN  = "#1E4D2B"
C_BLUE   = "#2B6CB0"
C_ORANGE = "#D97706"
C_GRAY   = "#718096"
C_GOLD   = "#B7791F"
C_BG     = "#F7F8FA"

MODEL_COLORS = {
    "Dummy Majority":    C_GRAY,
    "Dummy Stratified":  "#A0AEC0",
    "Logistic Reg.":     C_ORANGE,
    "Random Forest":     C_BLUE,
    "XGBoost":           C_GREEN,
    "RF + class_weight": C_RED,    # modelo final
}

PREFIX = "gold_v2/model_results/"


# ── Carga de datos ──────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _load(name: str) -> pd.DataFrame | None:
    return load_parquet_from_s3(key=PREFIX + name + ".parquet")


def _check(df, name):
    if df is None or df.empty:
        st.error(f"No se encontró {name} en S3. Ejecuta la celda de exportación del notebook.")
        return False
    return True


# ── Gráficas individuales ───────────────────────────────────────────────────

def _chart_metricas(df: pd.DataFrame):
    """Barras agrupadas: comparación de modelos en las 5 métricas clave."""
    metricas = ["pR_AUC", "roc_AUC", "f1", "recall", "precision"]
    labels   = ["PR-AUC", "ROC-AUC", "F1", "Recall", "Precision"]

    fig = go.Figure()
    for _, row in df.iterrows():
        valores = [row.get(m, 0) for m in metricas]
        color   = MODEL_COLORS.get(row["modelo"], C_GRAY)
        width   = 3 if row["es_final"] else 1
        fig.add_trace(go.Bar(
            name=row["modelo"],
            x=labels,
            y=valores,
            marker_color=color,
            marker_line_width=width,
            marker_line_color="white",
            opacity=1.0 if row["es_final"] else 0.55,
        ))

    fig.update_layout(
        barmode="group",
        plot_bgcolor=C_BG,
        paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.25),
        yaxis=dict(range=[0, 1.05], tickformat=".0%", gridcolor="#E2E8F0"),
        margin=dict(t=20, b=10),
        height=380,
    )
    fig.add_hline(y=0.8, line_dash="dot", line_color=C_GRAY,
                  annotation_text="Meta 80 %", annotation_position="top right")
    return fig


def _chart_feature_importance(df: pd.DataFrame, top_n: int = 15):
    """Barras horizontales ordenadas (Vocabulario: Magnitud / Ranking)."""
    # La columna se llama mean_abs_shap (del análisis SHAP del notebook)
    val_col = "mean_abs_shap" if "mean_abs_shap" in df.columns else "importance"
    df_top = df.nlargest(top_n, val_col).sort_values(val_col)
    colors = [C_RED if i == len(df_top) - 1 else C_BLUE
              for i in range(len(df_top))]

    fig = go.Figure(go.Bar(
        x=df_top[val_col],
        y=df_top["feature"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.3f}" for v in df_top[val_col]],
        textposition="outside",
    ))
    fig.update_layout(
        plot_bgcolor=C_BG,
        paper_bgcolor="white",
        xaxis=dict(title="Importancia SHAP media", gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=11)),
        margin=dict(t=10, b=10),
        height=max(320, top_n * 26),
    )
    return fig


def _chart_roc(df_roc: pd.DataFrame, df_fiscal: pd.DataFrame):
    """Línea ROC."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_roc["fpr"], y=df_roc["tpr"],
        mode="lines", name="Modelo final (RF)",
        line=dict(color=C_RED, width=2.5),
        fill="tozeroy", fillcolor="rgba(192,41,43,0.08)",
    ))
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines", name="Aleatorio",
        line=dict(color=C_GRAY, dash="dot", width=1.5),
    ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title="FPR (1 - Especificidad)", range=[0, 1], gridcolor="#E2E8F0"),
        yaxis=dict(title="TPR (Recall)", range=[0, 1.02], gridcolor="#E2E8F0"),
        legend=dict(orientation="h", y=-0.25),
        margin=dict(t=10, b=10), height=380,
    )
    return fig


def _chart_pr(df_pr: pd.DataFrame, df_fiscal: pd.DataFrame):
    """Curva Precision-Recall."""
    df_clean = df_pr.dropna()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_clean["recall"], y=df_clean["precision"],
        mode="lines", name="Modelo final (RF)",
        line=dict(color=C_BLUE, width=2.5),
        fill="tozeroy", fillcolor="rgba(43,108,176,0.08)",
    ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title="Recall", range=[0, 1], gridcolor="#E2E8F0"),
        yaxis=dict(title="Precision", range=[0, 1.02], gridcolor="#E2E8F0"),
        legend=dict(orientation="h", y=-0.25),
        margin=dict(t=10, b=10), height=380,
    )
    return fig


def _chart_confusion(df: pd.DataFrame):
    """Heatmap de la matriz de confusión."""
    pivot = df.pivot(index="real", columns="predicho", values="count").fillna(0)
    labels_r = pivot.index.tolist()
    labels_c = pivot.columns.tolist()
    z = pivot.values

    total = z.sum()
    text  = [[f"{int(v)}<br>({v/total:.1%})" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z, x=labels_c, y=labels_r,
        text=text, texttemplate="%{text}",
        colorscale=[[0, "#EBF4FF"], [1, C_RED]],
        showscale=False,
    ))
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(title="Predicción"),
        yaxis=dict(title="Real", autorange="reversed"),
        margin=dict(t=10, b=10), height=300,
    )
    return fig


def _chart_generalizacion(df: pd.DataFrame):
    """Slope chart: val → test por métrica. Schema: {metrica, val, test}."""
    fig = go.Figure()
    for _, row in df.iterrows():
        met    = row["metrica"]
        v_val  = float(row["val"])
        v_test = float(row["test"])
        delta  = v_test - v_val
        color  = C_GREEN if delta >= 0 else C_RED
        fig.add_trace(go.Scatter(
            x=["Validación", "Test"], y=[v_val, v_test],
            mode="lines+markers+text",
            name=met,
            line=dict(color=color, width=2),
            marker=dict(size=9, color=color),
            text=[f"{v_val:.3f}", f"{v_test:.3f}"],
            textposition="middle right",
        ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(gridcolor="#E2E8F0"),
        yaxis=dict(range=[0, 1.1], tickformat=".0%", gridcolor="#E2E8F0"),
        showlegend=True,
        legend=dict(orientation="h", y=-0.25),
        margin=dict(t=10, b=10), height=360,
    )
    return fig


def _chart_fiscal(df: pd.DataFrame):
    """Barras divergentes centradas en cero: pérdida (rojo) vs ahorro (verde)."""
    def _val(esc):
        r = df[df["escenario"] == esc]["perdida_usd"]
        return float(r.iloc[0]) if not r.empty else 0.0
    multa_total = _val("Sin modelo (todo incumple)")
    perdida     = _val("Con modelo final")
    ahorro      = _val("Ahorro estimado")
    categorias  = ["Multas Totales", "Pérdida\n(Falsos Neg.)", "Ahorro\n(Verdaderos Pos.)"]
    valores     = [multa_total, -perdida, ahorro]
    colores     = [C_GRAY, C_RED, C_GREEN]

    fig = go.Figure(go.Bar(
        x=categorias, y=valores,
        marker_color=colores,
        text=[f"${abs(v)/1e6:.1f}M" for v in valores],
        textposition="outside",
    ))
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        yaxis=dict(tickformat="$,.0f", gridcolor="#E2E8F0"),
        margin=dict(t=10, b=10), height=320,
    )
    return fig


def _chart_waterfall_fiscal(df: pd.DataFrame):
    """Waterfall: exposición total → pérdida residual → ahorro neto."""
    def _val(esc):
        r = df[df["escenario"] == esc]["perdida_usd"]
        return float(r.iloc[0]) if not r.empty else 0.0
    multa_total = _val("Sin modelo (todo incumple)")
    perdida     = _val("Con modelo final")
    ahorro      = _val("Ahorro estimado")

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["Exposición total<br>(sin modelo)", "Pérdida residual<br>(FN)", "Ahorro neto<br>con modelo"],
        y=[multa_total, -(multa_total - perdida), perdida],
        text=[f"${multa_total/1e6:.1f}M", f"-${(multa_total-perdida)/1e6:.1f}M", f"${perdida/1e6:.1f}M"],
        textposition="outside",
        connector=dict(line=dict(color=C_GRAY, width=1, dash="dot")),
        increasing=dict(marker=dict(color=C_RED)),
        decreasing=dict(marker=dict(color=C_GREEN)),
        totals=dict(marker=dict(color=C_ORANGE)),
    ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        yaxis=dict(tickformat="$,.0f", gridcolor="#E2E8F0", title="USD"),
        margin=dict(t=20, b=10), height=340,
        showlegend=False,
    )
    return fig


def _chart_radar(df: pd.DataFrame):
    """Radar/spider: perfil del modelo final vs mejores competidores."""
    metricas_r = ["pR_AUC", "roc_AUC", "f1", "recall", "precision"]
    labels_r   = ["PR-AUC", "ROC-AUC", "F1", "Recall", "Precision"]

    # Seleccionar: modelo final + 3 competidores relevantes
    candidatos = ["Modelo Final (test)", "RF + cw (v2)", "XGBoost + spw", "Logistic Reg."]
    df_sel = df[df["modelo"].isin(candidatos)].copy()
    if df_sel.empty:
        # fallback: top 4 por PR-AUC
        df_sel = df.nlargest(4, "pR_AUC")

    fig = go.Figure()
    palette = [C_RED, C_BLUE, C_GREEN, C_ORANGE, C_GRAY]
    for i, (_, row) in enumerate(df_sel.iterrows()):
        vals = [float(row.get(m, 0)) for m in metricas_r]
        vals_closed = vals + [vals[0]]  # cerrar el polígono
        fig.add_trace(go.Scatterpolar(
            r=vals_closed,
            theta=labels_r + [labels_r[0]],
            fill="toself",
            fillcolor=palette[i % len(palette)].replace(")", ", 0.10)").replace("rgb", "rgba") if palette[i].startswith("rgb") else palette[i] + "1A",
            line=dict(color=palette[i % len(palette)], width=2),
            name=row["modelo"],
            opacity=1.0 if row.get("es_final") else 0.75,
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], tickformat=".0%", gridcolor="#E2E8F0"),
            angularaxis=dict(gridcolor="#E2E8F0"),
            bgcolor=C_BG,
        ),
        paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.15),
        margin=dict(t=20, b=20), height=400,
    )
    return fig


def _chart_scatter_tradeoff(df: pd.DataFrame):
    """Bubble: Recall (x) vs Precision (y), tamaño = F1, destaca modelo final."""
    fig = go.Figure()
    for _, row in df.iterrows():
        es_final = bool(row.get("es_final", False))
        color  = C_RED if es_final else MODEL_COLORS.get(row["modelo"], C_GRAY)
        size   = max(float(row.get("f1", 0.1)) * 60, 8)
        symbol = "star" if es_final else "circle"
        fig.add_trace(go.Scatter(
            x=[row.get("recall", 0)],
            y=[row.get("precision", 0)],
            mode="markers+text",
            name=row["modelo"],
            text=[row["modelo"]],
            textposition="top center",
            marker=dict(color=color, size=size, symbol=symbol,
                        line=dict(color="white", width=1.5)),
        ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title="Recall", range=[-0.05, 1.05], tickformat=".0%", gridcolor="#E2E8F0"),
        yaxis=dict(title="Precision", range=[-0.05, 1.05], tickformat=".0%", gridcolor="#E2E8F0"),
        showlegend=False,
        margin=dict(t=20, b=10), height=380,
    )
    # Diagonal ideal
    fig.add_shape(type="line", x0=0, y0=1, x1=1, y1=0,
                  line=dict(color=C_GRAY, dash="dot", width=1))
    return fig


def _chart_lift(df_roc: pd.DataFrame):
    """Curva de Lift: cuántas veces mejor es el modelo vs selección aleatoria."""
    fpr = df_roc["fpr"].values
    tpr = df_roc["tpr"].values

    # Lift = TPR / FPR (con suavizado para evitar div/0)
    with __import__("numpy") as np:
        fpr_safe = np.where(fpr < 0.001, 0.001, fpr)
        lift     = tpr / fpr_safe
        # Solo hasta FPR=0.5 para que sea legible
        mask = fpr <= 0.5
        fpr_plot  = fpr[mask]
        lift_plot = lift[mask]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fpr_plot, y=lift_plot,
        mode="lines", name="Lift del modelo",
        line=dict(color=C_RED, width=2.5),
        fill="tozeroy", fillcolor="rgba(192,41,43,0.08)",
    ))
    fig.add_hline(y=1, line_dash="dot", line_color=C_GRAY,
                  annotation_text="Sin modelo (lift=1)", annotation_position="top right")
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title="Proporción de casos revisados (FPR)", tickformat=".0%", gridcolor="#E2E8F0"),
        yaxis=dict(title="Lift (veces mejor vs aleatorio)", gridcolor="#E2E8F0"),
        margin=dict(t=20, b=10), height=340,
    )
    return fig


# ── Sección principal ───────────────────────────────────────────────────────

def render_model_section():
    st.header("🤖 Modelo Predictivo — Resultados")
    st.markdown("Resultados del modelo **RF + class_weight** entrenado sobre la capa Gold de NY-311.")

    # Cargar todos los datasets
    df_metricas = _load("metricas_modelos")
    df_imp      = _load("feature_importance")
    df_roc      = _load("curva_roc")
    df_pr       = _load("curva_pr")
    df_cm       = _load("confusion_matrix_test")
    df_fiscal   = _load("resumen_fiscal")
    df_gen      = _load("generalizacion_val_vs_test")

    # ── KPIs rápidos ──────────────────────────────────────────────────────
    if _check(df_metricas, "métricas") and _check(df_fiscal, "resumen fiscal"):
        final = df_metricas[df_metricas["es_final"] == True].iloc[0]

        k1, k2, k3, k4 = st.columns(4)
        def _fsc_val(esc):
            r = df_fiscal[df_fiscal["escenario"] == esc]["perdida_usd"]
            return float(r.iloc[0]) if not r.empty else 0.0
        k1.metric("PR-AUC (final)", f"{final['pR_AUC']:.3f}")
        k2.metric("ROC-AUC (final)", f"{final['roc_AUC']:.3f}")
        k3.metric("Recall", f"{final['recall']:.1%}")
        k4.metric("Ahorro Fiscal", f"${_fsc_val('Ahorro estimado')/1e6:.1f}M USD")

        st.divider()

    # ── Tab layout ────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5, t6 = st.tabs([
        "📊 Comparación de Modelos",
        "🕷️ Perfil del Modelo",
        "🔍 Variables Clave (SHAP)",
        "📈 Curvas ROC / PR / Lift",
        "🎯 Matriz de Confusión",
        "💰 Impacto Fiscal & Generalización",
    ])

    with t1:
        st.subheader("Comparación de todos los modelos — métricas clave")
        if _check(df_metricas, "métricas"):
            st.plotly_chart(_chart_metricas(df_metricas), use_container_width=True)
            st.divider()
            st.subheader("Tradeoff Recall vs Precision (tamaño = F1)")
            st.caption("El modelo final (★) debe estar arriba-derecha respecto a los baselines.")
            if _check(df_metricas, "métricas"):
                st.plotly_chart(_chart_scatter_tradeoff(df_metricas), use_container_width=True)
            with st.expander("Ver tabla completa"):
                cols_show = ["modelo", "pR_AUC", "roc_AUC", "f1", "recall", "precision"]
                st.dataframe(
                    df_metricas[cols_show].style.format(
                        {c: "{:.3f}" for c in cols_show[1:]}
                    ),
                    use_container_width=True,
                )

    with t2:
        st.subheader("Perfil del modelo final vs competidores")
        st.caption("Radar de 5 métricas. Área mayor = mejor modelo en todas las dimensiones.")
        if _check(df_metricas, "métricas"):
            st.plotly_chart(_chart_radar(df_metricas), use_container_width=True)

    with t3:
        st.subheader("Variables más influyentes (SHAP mean |value|)")
        if _check(df_imp, "feature importance"):
            top_n = st.slider("Top N variables", 5, min(30, len(df_imp)), 15, key="top_n_shap")
            st.plotly_chart(_chart_feature_importance(df_imp, top_n), use_container_width=True)

    with t4:
        col_roc, col_pr = st.columns(2)
        with col_roc:
            st.subheader("Curva ROC")
            if _check(df_roc, "curva ROC"):
                if df_metricas is not None and not df_metricas.empty:
                    final_row = df_metricas[df_metricas["es_final"] == True]
                    if not final_row.empty:
                        st.caption(f"AUC = {final_row.iloc[0]['roc_AUC']:.4f}")
                st.plotly_chart(_chart_roc(df_roc, df_fiscal), use_container_width=True)
        with col_pr:
            st.subheader("Curva Precision-Recall")
            if _check(df_pr, "curva PR"):
                if df_metricas is not None and not df_metricas.empty:
                    final_row = df_metricas[df_metricas["es_final"] == True]
                    if not final_row.empty:
                        st.caption(f"AUC = {final_row.iloc[0]['pR_AUC']:.4f}")
                st.plotly_chart(_chart_pr(df_pr, df_fiscal), use_container_width=True)
        st.divider()
        st.subheader("Curva de Lift")
        st.caption("Lift = cuántas veces más incumplimientos detecta el modelo vs revisión aleatoria al mismo esfuerzo.")
        if _check(df_roc, "curva ROC"):
            st.plotly_chart(_chart_lift(df_roc), use_container_width=True)

    with t5:
        st.subheader("Matriz de Confusión — conjunto test")
        if _check(df_cm, "matriz de confusión"):
            st.caption("Threshold aplicado: **0.50**")
            c_cm, c_exp = st.columns([1, 1])
            with c_cm:
                st.plotly_chart(_chart_confusion(df_cm), use_container_width=True)
            with c_exp:
                tn = int(df_cm[(df_cm["real"] == 0) & (df_cm["predicho"] == 0)]["count"].sum())
                fp = int(df_cm[(df_cm["real"] == 0) & (df_cm["predicho"] == 1)]["count"].sum())
                fn = int(df_cm[(df_cm["real"] == 1) & (df_cm["predicho"] == 0)]["count"].sum())
                tp = int(df_cm[(df_cm["real"] == 1) & (df_cm["predicho"] == 1)]["count"].sum())
                total = tn + fp + fn + tp
                st.markdown(f"""
| Cuadrante | Valor | Interpretación |
|-----------|------:|----------------|
| **VP** (detectados correctamente) | {tp:,} | {tp/total:.1%} del total |
| **FN** (incumplimientos no detectados) | {fn:,} | ⚠️ riesgo fiscal no capturado |
| **FP** (falsas alarmas) | {fp:,} | revisión innecesaria |
| **VN** (cumplimientos correctos) | {tn:,} | {tn/total:.1%} del total |
""")

    with t6:
        col_f, col_g = st.columns(2)
        with col_f:
            st.subheader("Impacto Fiscal — Waterfall")
            st.caption("Cascada: exposición total → reducción lograda → pérdida residual.")
            if _check(df_fiscal, "resumen fiscal"):
                def _fv(esc):
                    r = df_fiscal[df_fiscal["escenario"] == esc]["perdida_usd"]
                    return float(r.iloc[0]) if not r.empty else 0.0
                perdida = _fv("Con modelo final")
                st.caption(f"Pérdida residual: **${perdida/1e6:.1f}M USD**")
                st.plotly_chart(_chart_waterfall_fiscal(df_fiscal), use_container_width=True)
        with col_g:
            st.subheader("Generalización: Validación → Test")
            st.caption("Pendiente negativa = degradación entre splits.")
            if _check(df_gen, "generalización"):
                st.plotly_chart(_chart_generalizacion(df_gen), use_container_width=True)
