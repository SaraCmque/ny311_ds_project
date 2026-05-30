"""
model_component.py
Visualización de resultados del modelo predictivo NY-311.
Gráficas basadas en el FT Visual Vocabulary:
  - RANKING     → Lollipop (comparación de modelos, feature importance)
  - CORRELACIÓN → Scatter/Bubble con iso-F1 (tradeoff Recall-Precision)
  - CAMBIO      → Slope chart (generalización val→test)
  - FLUJO       → Waterfall (impacto fiscal)
  - DISTRIBUCIÓN → Heatmap anotado (matriz de confusión)
  - MAGNITUD    → Barras horizontales ordenadas (SHAP)
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from s3_utils import load_parquet_from_s3

# ── Paleta ──────────────────────────────────────────────────────────────────
C_RED    = "#C0292B"
C_GREEN  = "#1E4D2B"
C_BLUE   = "#2B6CB0"
C_ORANGE = "#D97706"
C_GRAY   = "#718096"
C_GOLD   = "#B7791F"
C_LIGHT  = "#A0AEC0"
C_BG     = "#F7F8FA"
C_GRID   = "#E2E8F0"

_MODEL_COLOR = {
    "Dummy Stratified":    C_LIGHT,
    "Dummy Majority":      C_LIGHT,
    "Dummy Constant1":     C_LIGHT,
    "Logistic Reg.":       C_ORANGE,
    "LR + class_weight":   C_ORANGE,
    "Random Forest":       C_BLUE,
    "RF + class_weight":   C_BLUE,
    "RF + cw (v2)":        C_BLUE,
    "XGBoost":             C_GREEN,
    "XGBoost + spw":       C_GREEN,
    "XGB + spw (v2)":      C_GREEN,
    "XGB sin bal. (v2)":   C_GREEN,
    "Modelo Final (test)": C_RED,
}

PREFIX = "gold_v2/model_results/"


# ── Utilidades ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _load(name: str) -> pd.DataFrame | None:
    return load_parquet_from_s3(key=PREFIX + name + ".parquet")


def _check(df, label: str) -> bool:
    if df is None or df.empty:
        st.warning(f"Sin datos: **{label}**")
        return False
    return True


def _fsc(df_fiscal: pd.DataFrame, escenario: str) -> float:
    r = df_fiscal[df_fiscal["escenario"] == escenario]["perdida_usd"]
    return float(r.iloc[0]) if not r.empty else 0.0


# ── 1. LOLLIPOP — Ranking de modelos ────────────────────────────────────────
def _chart_lollipop(df: pd.DataFrame, metrica: str, label: str) -> go.Figure:
    """RANKING — Lollipop horizontal ordenado. Visual Vocabulary: Ranking."""
    df_s = df.sort_values(metrica, ascending=True).copy()
    colors = [C_RED if bool(r) else _MODEL_COLOR.get(str(m), C_GRAY)
              for m, r in zip(df_s["modelo"], df_s["es_final"])]
    ys = list(range(len(df_s)))

    fig = go.Figure()
    for i, (_, row) in enumerate(df_s.iterrows()):
        fig.add_shape(type="line", x0=0, x1=float(row[metrica]), y0=i, y1=i,
                      line=dict(color=colors[i], width=2))
    fig.add_trace(go.Scatter(
        x=df_s[metrica].tolist(), y=ys,
        mode="markers+text",
        marker=dict(color=colors, size=13, line=dict(color="white", width=1.5)),
        text=[f" {v:.3f}" for v in df_s[metrica]],
        textposition="middle right",
        hovertext=df_s["modelo"].tolist(),
        hoverinfo="text+x",
        showlegend=False,
    ))
    final_val = df_s[df_s["es_final"] == True][metrica]
    if not final_val.empty:
        fig.add_vline(x=float(final_val.iloc[0]), line_dash="dot", line_color=C_RED,
                      annotation_text="Modelo final", annotation_position="top",
                      annotation_font=dict(color=C_RED, size=11))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title=label, range=[0, 1.08], tickformat=".0%", gridcolor=C_GRID),
        yaxis=dict(tickmode="array", tickvals=ys,
                   ticktext=df_s["modelo"].tolist(), gridcolor=C_GRID),
        margin=dict(t=30, l=190, r=70, b=30),
        height=max(360, len(df_s) * 34),
    )
    return fig


# ── 2. BARRAS HORIZONTALES — SHAP Feature Importance (MAGNITUD) ──────────────
def _chart_shap(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """MAGNITUD — Barras horizontales ordenadas. Visual Vocabulary: Magnitude."""
    col = "mean_abs_shap" if "mean_abs_shap" in df.columns else df.columns[-1]
    df_top = df.nlargest(top_n, col).sort_values(col, ascending=True)
    n = len(df_top)
    colors = [C_RED if i >= n - 3 else C_BLUE if i >= n - 8 else C_GRAY
              for i in range(n)]
    fig = go.Figure(go.Bar(
        x=df_top[col].tolist(), y=df_top["feature"].tolist(),
        orientation="h", marker_color=colors,
        text=[f"{v:.4f}" for v in df_top[col]], textposition="outside",
        hovertemplate="%{y}: %{x:.4f}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title="Importancia SHAP media |valor|", gridcolor=C_GRID),
        yaxis=dict(tickfont=dict(size=11)),
        margin=dict(t=10, l=10, r=70, b=30),
        height=max(340, n * 28),
    )
    return fig


# ── 3. BUBBLE CHART — Tradeoff Recall/Precision (CORRELACIÓN) ────────────────
def _chart_bubble(df: pd.DataFrame) -> go.Figure:
    """CORRELACIÓN — Bubble chart con iso-F1. Visual Vocabulary: Correlation."""
    fig = go.Figure()
    # Iso-F1 curves
    for f1_iso in [0.2, 0.4, 0.6, 0.8]:
        r = np.linspace(0.01, 1, 300)
        denom = 2 * r - f1_iso
        with np.errstate(divide="ignore", invalid="ignore"):
            p = np.where(denom > 0, f1_iso * r / denom, np.nan)
        mask = (p >= 0) & (p <= 1) & np.isfinite(p)
        fig.add_trace(go.Scatter(
            x=r[mask].tolist(), y=p[mask].tolist(), mode="lines",
            line=dict(color=C_GRID, width=1, dash="dot"),
            hoverinfo="skip", showlegend=False,
        ))
        if mask.sum() > 0:
            fig.add_annotation(
                x=float(r[mask][-1]), y=float(p[mask][-1]),
                text=f"F1={f1_iso}", showarrow=False,
                font=dict(size=9, color=C_GRAY), xanchor="left",
            )
    for _, row in df.iterrows():
        es_final = bool(row.get("es_final", False))
        color  = C_RED if es_final else _MODEL_COLOR.get(str(row["modelo"]), C_GRAY)
        size   = max(float(row.get("f1", 0.05)) * 55, 10)
        symbol = "star" if es_final else "circle"
        nombre = str(row["modelo"]) + (" ★" if es_final else "")
        fig.add_trace(go.Scatter(
            x=[float(row.get("recall", 0))],
            y=[float(row.get("precision", 0))],
            mode="markers+text",
            marker=dict(color=color, size=size, symbol=symbol,
                        line=dict(color="white", width=1.5), opacity=0.88),
            text=[nombre], textposition="top center", textfont=dict(size=10),
            hovertemplate=(f"<b>{row['modelo']}</b><br>"
                           f"Recall={row.get('recall',0):.3f}<br>"
                           f"Precision={row.get('precision',0):.3f}<br>"
                           f"F1={row.get('f1',0):.3f}<extra></extra>"),
            showlegend=False,
        ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title="Recall", range=[-0.03, 1.08], tickformat=".0%", gridcolor=C_GRID),
        yaxis=dict(title="Precision", range=[-0.03, 1.12], tickformat=".0%", gridcolor=C_GRID),
        margin=dict(t=20, b=30, l=60, r=20), height=430,
    )
    return fig


# ── 4. CURVA ROC ──────────────────────────────────────────────────────────────
def _chart_roc(df_roc: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_roc["fpr"].tolist(), y=df_roc["tpr"].tolist(), mode="lines",
        name="Modelo final (RF)", line=dict(color=C_RED, width=2.5),
        fill="tozeroy", fillcolor="rgba(192,41,43,0.08)",
        hovertemplate="FPR=%{x:.3f} | TPR=%{y:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines", name="Clasificador aleatorio",
        line=dict(color=C_GRAY, dash="dot", width=1.5), hoverinfo="skip",
    ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title="FPR (1 − Especificidad)", range=[0, 1],
                   tickformat=".0%", gridcolor=C_GRID),
        yaxis=dict(title="TPR (Recall)", range=[0, 1.02],
                   tickformat=".0%", gridcolor=C_GRID),
        legend=dict(orientation="h", y=-0.25),
        margin=dict(t=10, b=10), height=380,
    )
    return fig


# ── 5. CURVA PRECISION-RECALL ─────────────────────────────────────────────────
def _chart_pr(df_pr: pd.DataFrame) -> go.Figure:
    df_c = df_pr.dropna().sort_values("recall")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_c["recall"].tolist(), y=df_c["precision"].tolist(), mode="lines",
        name="Modelo final (RF)", line=dict(color=C_BLUE, width=2.5),
        fill="tozeroy", fillcolor="rgba(43,108,176,0.08)",
        hovertemplate="Recall=%{x:.3f} | Precision=%{y:.3f}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title="Recall", range=[0, 1], tickformat=".0%", gridcolor=C_GRID),
        yaxis=dict(title="Precision", range=[0, 1.02], tickformat=".0%", gridcolor=C_GRID),
        legend=dict(orientation="h", y=-0.25),
        margin=dict(t=10, b=10), height=380,
    )
    return fig


# ── 6. CURVA DE LIFT ──────────────────────────────────────────────────────────
def _chart_lift(df_roc: pd.DataFrame) -> go.Figure:
    """CAMBIO — Lift curve. Visual Vocabulary: Change over time."""
    fpr = df_roc["fpr"].values.copy()
    tpr = df_roc["tpr"].values.copy()
    fpr_safe = np.where(fpr < 0.001, 0.001, fpr)
    lift = tpr / fpr_safe
    mask = (fpr >= 0.001) & (fpr <= 0.50)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fpr[mask].tolist(), y=lift[mask].tolist(), mode="lines",
        name="Lift", line=dict(color=C_RED, width=2.5),
        fill="tozeroy", fillcolor="rgba(192,41,43,0.08)",
        hovertemplate="Revisados=%{x:.1%} | Lift=%{y:.2f}×<extra></extra>",
    ))
    fig.add_hline(y=1, line_dash="dot", line_color=C_GRAY,
                  annotation_text="Sin modelo (lift = 1×)",
                  annotation_position="top right",
                  annotation_font=dict(color=C_GRAY, size=11))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(title="Proporción de quejas revisadas", tickformat=".0%", gridcolor=C_GRID),
        yaxis=dict(title="Lift (× mejor que aleatorio)", gridcolor=C_GRID),
        margin=dict(t=20, b=10), height=340,
    )
    return fig


# ── 7. HEATMAP — Matriz de Confusión (DISTRIBUCIÓN) ──────────────────────────
def _chart_confusion(df_cm: pd.DataFrame) -> go.Figure:
    """DISTRIBUCIÓN — Heatmap 2×2 con etiquetas. Visual Vocabulary: Distribution."""
    df_m = df_cm.copy()
    df_m["real"]     = df_m["real"].map({0: "CUMPLE", 1: "INCUMPLE"})
    df_m["predicho"] = df_m["predicho"].map({0: "CUMPLE", 1: "INCUMPLE"})
    orden = ["CUMPLE", "INCUMPLE"]
    pivot = (df_m.pivot(index="real", columns="predicho", values="count")
               .reindex(index=orden, columns=orden).fillna(0))
    z = pivot.values
    total = z.sum()
    text = [[f"<b>{int(v):,}</b><br>{v/total:.1%}" for v in fila] for fila in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=orden, y=orden,
        text=text, texttemplate="%{text}", textfont=dict(size=14),
        colorscale=[[0, "#EBF8EE"], [0.4, "#FEF3C7"], [1.0, C_RED]],
        showscale=False,
        hovertemplate="Real=%{y} | Pred=%{x}<br>N=%{z:,}<extra></extra>",
    ))
    # Etiquetas de cuadrante (VN / FP / FN / VP)
    for ri, ci, etiq, col in [
        (0, 0, "VN", C_GREEN), (0, 1, "FP", C_ORANGE),
        (1, 0, "FN", C_RED),   (1, 1, "VP", C_GREEN),
    ]:
        fig.add_annotation(x=ci, y=ri, text=etiq, showarrow=False,
                           xshift=34, yshift=20,
                           font=dict(size=12, color=col, family="Arial Black"))
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(title="Predicción del modelo", side="bottom"),
        yaxis=dict(title="Valor real", autorange="reversed"),
        margin=dict(t=20, b=20), height=340,
    )
    return fig


# ── 8. SLOPE CHART — Generalización val→test (CAMBIO) ────────────────────────
def _chart_slope(df_gen: pd.DataFrame) -> go.Figure:
    """CAMBIO — Slope chart. Visual Vocabulary: Change between two points."""
    fig = go.Figure()
    for _, row in df_gen.iterrows():
        v_val  = float(row["val"])
        v_test = float(row["test"])
        delta  = v_test - v_val
        color  = C_GREEN if delta >= -0.005 else C_RED
        met    = str(row["metrica"])
        fig.add_trace(go.Scatter(
            x=["Validación", "Test"], y=[v_val, v_test],
            mode="lines+markers", name=met,
            line=dict(color=color, width=2.2),
            marker=dict(size=10, color=color, line=dict(color="white", width=1)),
            hovertemplate=f"<b>{met}</b><br>%{{x}}: %{{y:.3f}}<extra></extra>",
        ))
        fig.add_annotation(x="Validación", y=v_val, text=f"{v_val:.3f}",
                           xanchor="right", showarrow=False,
                           font=dict(size=10, color=color), xshift=-8)
        fig.add_annotation(x="Test", y=v_test, text=f"{v_test:.3f}",
                           xanchor="left", showarrow=False,
                           font=dict(size=10, color=color), xshift=8)
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        xaxis=dict(gridcolor=C_GRID, tickfont=dict(size=13, color="#2D3748")),
        yaxis=dict(range=[0, 1.08], tickformat=".0%", gridcolor=C_GRID),
        legend=dict(orientation="v", x=1.01, y=0.5),
        margin=dict(t=20, b=20, l=70, r=150), height=360,
    )
    return fig


# ── 9. WATERFALL — Impacto Fiscal (FLUJO) ────────────────────────────────────
def _chart_waterfall(df_fiscal: pd.DataFrame) -> go.Figure:
    """FLUJO — Waterfall chart. Visual Vocabulary: Flow."""
    multa  = _fsc(df_fiscal, "Sin modelo (todo incumple)")
    ahorro = _fsc(df_fiscal, "Ahorro estimado")
    perdida = _fsc(df_fiscal, "Con modelo final")
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["Exposición total<br>(sin modelo)", "Ahorro del modelo<br>(incumplimientos detectados)", "Pérdida residual<br>(FN no detectados)"],
        y=[multa, -ahorro, perdida],
        text=[f"${multa/1e6:.1f}M", f"−${ahorro/1e6:.1f}M", f"${perdida/1e6:.1f}M"],
        textposition="outside", textfont=dict(size=13),
        connector=dict(line=dict(color=C_GRAY, width=1, dash="dot")),
        increasing=dict(marker=dict(color=C_RED)),
        decreasing=dict(marker=dict(color=C_GREEN)),
        totals=dict(marker=dict(color=C_ORANGE)),
        hovertemplate="%{x}: %{text}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor=C_BG, paper_bgcolor="white",
        yaxis=dict(tickformat="$,.0f", title="USD", gridcolor=C_GRID),
        margin=dict(t=30, b=10, l=10, r=10), height=380,
        showlegend=False,
    )
    return fig


# ── SECCIÓN PRINCIPAL ─────────────────────────────────────────────────────────
def render_model_section():
    st.header("🤖 Modelo Predictivo — Resultados")
    st.markdown(
        "Resultados del modelo **Random Forest + class_weight** "
        "entrenado sobre la capa Gold de NY-311 para predecir incumplimiento del SLA."
    )

    df_metricas = _load("metricas_modelos")
    df_imp      = _load("feature_importance")
    df_roc      = _load("curva_roc")
    df_pr       = _load("curva_pr")
    df_cm       = _load("confusion_matrix_test")
    df_fiscal   = _load("resumen_fiscal")
    df_gen      = _load("generalizacion_val_vs_test")

    # ── KPIs ──────────────────────────────────────────────────────────────
    datos_ok = (df_metricas is not None and not df_metricas.empty and
                df_fiscal   is not None and not df_fiscal.empty)
    if datos_ok:
        final_rows = df_metricas[df_metricas["es_final"] == True]
        if not final_rows.empty:
            final   = final_rows.iloc[0]
            ahorro  = _fsc(df_fiscal, "Ahorro estimado")
            perdida = _fsc(df_fiscal, "Con modelo final")
            multa   = _fsc(df_fiscal, "Sin modelo (todo incumple)")
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("PR-AUC", f"{final['pR_AUC']:.3f}")
            k2.metric("ROC-AUC", f"{final['roc_AUC']:.3f}")
            k3.metric("Recall", f"{final['recall']:.1%}")
            k4.metric("Ahorro fiscal", f"${ahorro/1e6:.1f}M",
                      delta=f"−{ahorro/multa:.0%} exposición")
            k5.metric("Pérdida residual", f"${perdida/1e6:.1f}M",
                      delta=f"{perdida/multa:.0%} restante", delta_color="inverse")
            st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5, t6 = st.tabs([
        "📊 Ranking de Modelos",
        "🔍 Variables Clave (SHAP)",
        "📈 Curvas ROC / PR / Lift",
        "🎯 Matriz de Confusión",
        "📉 Generalización",
        "💰 Impacto Fiscal",
    ])

    with t1:
        if _check(df_metricas, "métricas"):
            label_map = {"pR_AUC": "PR-AUC", "roc_AUC": "ROC-AUC",
                         "f1": "F1", "recall": "Recall", "precision": "Precision"}
            metrica_sel = st.radio(
                "Ordenar por:", list(label_map.keys()),
                format_func=lambda x: label_map[x],
                horizontal=True, key="rank_metric",
            )
            st.subheader(f"Ranking de modelos — {label_map[metrica_sel]}")
            st.caption("Lollipop ordenado de menor a mayor. Punto rojo = modelo final en producción.")
            st.plotly_chart(
                _chart_lollipop(df_metricas, metrica_sel, label_map[metrica_sel]),
                use_container_width=True,
            )
            st.divider()
            st.subheader("Tradeoff Recall vs Precision")
            st.caption("Bubble chart: X = Recall, Y = Precision, tamaño = F1. "
                       "Líneas punteadas = iso-F1. ★ = modelo final.")
            st.plotly_chart(_chart_bubble(df_metricas), use_container_width=True)
            with st.expander("📋 Tabla completa"):
                cols = ["modelo", "pR_AUC", "roc_AUC", "f1", "recall", "precision"]
                st.dataframe(
                    df_metricas[cols].sort_values("pR_AUC", ascending=False)
                                     .style.format({c: "{:.3f}" for c in cols[1:]})
                                     .highlight_max(subset=cols[1:], color="#D1FAE5")
                                     .highlight_min(subset=cols[1:], color="#FEE2E2"),
                    use_container_width=True,
                )

    with t2:
        if _check(df_imp, "feature importance"):
            top_n = st.slider("Top N variables", 5, min(28, len(df_imp)), 15, key="top_n")
            st.subheader(f"Top {top_n} variables — importancia SHAP media")
            st.caption("Rojo = top 3 más influyentes, azul = top 4-8, gris = resto.")
            st.plotly_chart(_chart_shap(df_imp, top_n), use_container_width=True)

    with t3:
        c_roc, c_pr = st.columns(2)
        with c_roc:
            if _check(df_roc, "curva ROC") and _check(df_metricas, "métricas"):
                fr = df_metricas[df_metricas["es_final"] == True]
                auc = f"{fr.iloc[0]['roc_AUC']:.4f}" if not fr.empty else "—"
                st.subheader(f"Curva ROC · AUC = {auc}")
                st.caption("Discriminación entre clases. Mayor área = mejor modelo.")
                st.plotly_chart(_chart_roc(df_roc), use_container_width=True)
        with c_pr:
            if _check(df_pr, "curva PR") and _check(df_metricas, "métricas"):
                fr = df_metricas[df_metricas["es_final"] == True]
                auc = f"{fr.iloc[0]['pR_AUC']:.4f}" if not fr.empty else "—"
                st.subheader(f"Curva PR · AUC = {auc}")
                st.caption("Más relevante que ROC en clases desbalanceadas.")
                st.plotly_chart(_chart_pr(df_pr), use_container_width=True)
        st.divider()
        st.subheader("Curva de Lift")
        st.caption("Lift = cuántas veces más incumplimientos detecta el modelo "
                   "vs revisión aleatoria al mismo nivel de esfuerzo (FPR).")
        if _check(df_roc, "curva ROC"):
            st.plotly_chart(_chart_lift(df_roc), use_container_width=True)

    with t4:
        if _check(df_cm, "matriz de confusión"):
            st.subheader("Matriz de Confusión — conjunto test · Threshold = 0.50")
            c_left, c_right = st.columns([1, 1])
            with c_left:
                st.plotly_chart(_chart_confusion(df_cm), use_container_width=True)
            with c_right:
                tn = int(df_cm[(df_cm["real"] == 0) & (df_cm["predicho"] == 0)]["count"].sum())
                fp = int(df_cm[(df_cm["real"] == 0) & (df_cm["predicho"] == 1)]["count"].sum())
                fn = int(df_cm[(df_cm["real"] == 1) & (df_cm["predicho"] == 0)]["count"].sum())
                tp = int(df_cm[(df_cm["real"] == 1) & (df_cm["predicho"] == 1)]["count"].sum())
                total = tn + fp + fn + tp
                rec = tp / (tp + fn) if (tp + fn) > 0 else 0
                pre = tp / (tp + fp) if (tp + fp) > 0 else 0
                f1  = 2 * pre * rec / (pre + rec) if (pre + rec) > 0 else 0
                st.markdown(f"""
**Cuadrantes**

| | Cantidad | % total | Significado |
|---|---:|:---:|---|
| ✅ **VN** | {tn:,} | {tn/total:.1%} | Cumplió → predijo Cumple |
| ✅ **VP** | {tp:,} | {tp/total:.1%} | Incumplió → detectado |
| ⚠️ **FN** | {fn:,} | {fn/total:.1%} | Incumplió → no detectado |
| 🔵 **FP** | {fp:,} | {fp/total:.1%} | Cumplió → falsa alarma |

**Métricas derivadas**
- Recall: **{rec:.1%}**
- Precision: **{pre:.1%}**
- F1: **{f1:.3f}**
""")

    with t5:
        if _check(df_gen, "generalización"):
            st.subheader("Generalización: Validación → Test")
            st.caption("Verde = estable o mejora. Rojo = degradación (posible overfitting).")
            st.plotly_chart(_chart_slope(df_gen), use_container_width=True)
            with st.expander("📋 Ver tabla"):
                df_show = df_gen.copy()
                df_show["delta"] = df_show["test"] - df_show["val"]
                st.dataframe(
                    df_show.style.format({"val": "{:.3f}", "test": "{:.3f}", "delta": "{:+.3f}"}),
                    use_container_width=True,
                )

    with t6:
        if _check(df_fiscal, "resumen fiscal"):
            multa   = _fsc(df_fiscal, "Sin modelo (todo incumple)")
            perdida = _fsc(df_fiscal, "Con modelo final")
            ahorro  = _fsc(df_fiscal, "Ahorro estimado")
            pct_ah  = ahorro / multa if multa > 0 else 0
            st.subheader("Impacto Fiscal — Waterfall")
            st.caption(f"Cascada: exposición total → ahorro logrado ({pct_ah:.0%}).")
            st.plotly_chart(_chart_waterfall(df_fiscal), use_container_width=True)
            m1, m2 = st.columns(2)
            m1.metric("Exposición total", f"${multa/1e6:.1f}M", "sin modelo")
            m2.metric("Ahorro con modelo", f"${ahorro/1e6:.1f}M",
                      f"+{pct_ah:.0%} recuperado")

