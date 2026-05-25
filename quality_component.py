import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from s3_utils import load_from_s3

# ═══════════════════════════════════════════════════════════════
# DESIGN SYSTEM — LIGHT THEME
# ═══════════════════════════════════════════════════════════════

# Colores principales por capa
C_BRONZE       = "#B5651D"
C_BRONZE_LIGHT = "#FFF3E0"
C_BRONZE_MID   = "#FFCC80"

C_SILVER       = "#546E7A"
C_SILVER_LIGHT = "#ECEFF1"
C_SILVER_MID   = "#B0BEC5"

C_GOLD         = "#F9A825"
C_GOLD_LIGHT   = "#FFFDE7"
C_GOLD_MID     = "#FFE082"

C_SUCCESS = "#2E7D32"
C_DANGER  = "#C62828"
C_WARNING = "#E65100"
C_INFO    = "#1565C0"
C_BG      = "#FAFAFA"
C_BORDER  = "#E0E0E0"
C_TEXT    = "#212121"
C_MUTED   = "#757575"

FONT = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"

# ──────────────────────────────────────────────
# CSS GLOBAL
# ──────────────────────────────────────────────
def _inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Fondo general */
    .stApp { background-color: #F5F7FA; }

    /* ── Page Header ── */
    .qc-page-header {
        background: linear-gradient(135deg, #1A237E 0%, #283593 50%, #3949AB 100%);
        border-radius: 16px;
        padding: 36px 40px 28px;
        margin-bottom: 28px;
        color: white;
    }
    .qc-page-header h1 {
        font-family: Inter, sans-serif;
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 8px;
        letter-spacing: -0.5px;
    }
    .qc-page-header p {
        font-family: Inter, sans-serif;
        font-size: 0.95rem;
        opacity: 0.85;
        margin: 0;
        line-height: 1.6;
    }

    /* ── Layer badge ── */
    .layer-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 16px;
        border-radius: 24px;
        font-family: Inter, sans-serif;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .layer-bronze { background:#FFF3E0; color:#BF360C; border:1.5px solid #FFCC80; }
    .layer-silver { background:#ECEFF1; color:#37474F; border:1.5px solid #B0BEC5; }
    .layer-gold   { background:#FFFDE7; color:#E65100; border:1.5px solid #FFE082; }

    /* ── Section title ── */
    .section-title {
        font-family: Inter, sans-serif;
        font-size: 1.1rem;
        font-weight: 600;
        color: #1A237E;
        margin: 24px 0 4px;
        padding-bottom: 6px;
        border-bottom: 2px solid #E8EAF6;
    }
    .section-sub {
        font-family: Inter, sans-serif;
        font-size: 0.82rem;
        color: #757575;
        margin-bottom: 16px;
    }

    /* ── KPI cards ── */
    .kpi-row { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:20px; }
    .kpi-card {
        flex:1; min-width:140px;
        background:white;
        border-radius:12px;
        padding:18px 20px 14px;
        border:1px solid #E0E0E0;
        box-shadow:0 1px 4px rgba(0,0,0,.06);
        text-align:center;
    }
    .kpi-card .kpi-label {
        font-family:Inter,sans-serif; font-size:0.72rem;
        font-weight:600; text-transform:uppercase;
        letter-spacing:.6px; color:#9E9E9E; margin-bottom:6px;
    }
    .kpi-card .kpi-value {
        font-family:Inter,sans-serif; font-size:1.65rem;
        font-weight:700; color:#1A237E; line-height:1;
    }
    .kpi-card .kpi-delta {
        font-family:Inter,sans-serif; font-size:0.76rem;
        font-weight:500; margin-top:4px;
    }
    .kpi-pos { color:#2E7D32; } .kpi-neg { color:#C62828; } .kpi-neu { color:#757575; }

    /* ── Insight callout ── */
    .insight {
        background:white; border-left:4px solid #3949AB;
        border-radius:0 10px 10px 0; padding:12px 16px;
        margin:12px 0 20px; font-family:Inter,sans-serif;
        font-size:0.85rem; color:#37474F; line-height:1.6;
        box-shadow:0 1px 3px rgba(0,0,0,.07);
    }
    .insight strong { color:#1A237E; }

    /* ── Progress bar table ── */
    .prog-table { width:100%; border-collapse:collapse; font-family:Inter,sans-serif; font-size:0.83rem; }
    .prog-table th { background:#F5F7FA; color:#546E7A; padding:8px 12px;
                     text-align:left; font-weight:600; border-bottom:2px solid #E0E0E0; }
    .prog-table td { padding:7px 12px; border-bottom:1px solid #F0F0F0; vertical-align:middle; }
    .prog-table tr:hover { background:#F9F9FB; }
    .prog-bar-wrap { width:120px; background:#F0F0F0; border-radius:6px; height:8px; display:inline-block; }
    .prog-bar-fill { height:8px; border-radius:6px; }
    .chip { display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; }
    .chip-ok  { background:#E8F5E9; color:#2E7D32; }
    .chip-warn{ background:#FFF8E1; color:#E65100; }
    .chip-bad { background:#FFEBEE; color:#C62828; }

    /* ── Comparison pills ── */
    .pill-row { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:12px; }
    .pill {
        display:inline-flex; align-items:center; gap:6px;
        background:white; border:1.5px solid #E0E0E0;
        border-radius:20px; padding:5px 14px;
        font-family:Inter,sans-serif; font-size:0.8rem; font-weight:500; color:#37474F;
    }
    .dot { width:10px; height:10px; border-radius:50%; display:inline-block; }

    /* ── Chart card wrapper ── */
    .chart-card {
        background:white; border-radius:14px;
        padding:20px; border:1px solid #E0E0E0;
        box-shadow:0 2px 8px rgba(0,0,0,.05);
        margin-bottom:20px;
    }
    .chart-title {
        font-family:Inter,sans-serif; font-size:0.9rem;
        font-weight:600; color:#1A237E; margin-bottom:2px;
    }
    .chart-desc {
        font-family:Inter,sans-serif; font-size:0.78rem;
        color:#9E9E9E; margin-bottom:14px;
    }

    /* ── Overall score ring row ── */
    .score-row { display:flex; gap:16px; margin-bottom:28px; flex-wrap:wrap; }
    .score-card {
        flex:1; min-width:180px; background:white;
        border-radius:14px; padding:20px 16px;
        border:1px solid #E0E0E0;
        box-shadow:0 2px 8px rgba(0,0,0,.05);
        text-align:center;
    }
    </style>
    """, unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════════
# HELPERS — CALIDAD Y MÉTRICAS
# ═══════════════════════════════════════════════════════════════

def quality_score(df_meta: pd.DataFrame) -> float:
    if "nulos_pct" not in df_meta.columns:
        return 0.0
    return max(0.0, 100.0 - df_meta["nulos_pct"].mean())


def _score_color(score: float):
    if score >= 85:
        return C_SUCCESS, "#E8F5E9"
    if score >= 60:
        return C_WARNING, "#FFF8E1"
    return C_DANGER, "#FFEBEE"


def _null_chip(pct: float) -> str:
    if pct == 0:
        return '<span class="chip chip-ok">Sin nulos</span>'
    if pct < 10:
        return f'<span class="chip chip-warn">{pct:.1f}%</span>'
    return f'<span class="chip chip-bad">{pct:.1f}%</span>'


def _null_bar_html(pct: float, layer_color: str) -> str:
    fill = min(pct, 100)
    return (
        f'<div class="prog-bar-wrap">'
        f'<div class="prog-bar-fill" style="width:{fill}%;background:{layer_color};"></div>'
        f'</div>'
    )


# ───────────────────────────── CHART FACTORIES ──────────────────────────────

_LAYOUT_BASE = dict(
    font=dict(family=FONT, size=12, color=C_TEXT),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(t=48, b=40, l=16, r=16),
    hoverlabel=dict(bgcolor="white", font_size=12, font_family=FONT),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
    title=dict(font=dict(size=14, color=C_TEXT, family=FONT), x=0),
    xaxis=dict(gridcolor="#F0F0F0", linecolor=C_BORDER, tickfont=dict(size=11)),
    yaxis=dict(gridcolor="#F0F0F0", linecolor=C_BORDER, tickfont=dict(size=11)),
)


def _apply_base(fig: go.Figure, **extra) -> go.Figure:
    kw = {**_LAYOUT_BASE, **extra}
    fig.update_layout(**kw)
    return fig


def _gauge(score: float, label: str, color: str, bg: str) -> go.Figure:
    ink, _ = _score_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        delta={"reference": 80, "increasing": {"color": C_SUCCESS}, "decreasing": {"color": C_DANGER},
               "font": {"size": 13}},
        title={"text": label, "font": {"size": 13, "color": C_MUTED, "family": FONT}},
        number={"suffix": "%", "font": {"size": 32, "color": ink, "family": FONT}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": C_BORDER,
                     "tickfont": {"size": 10, "color": C_MUTED}},
            "bar": {"color": ink, "thickness": 0.28},
            "bgcolor": bg,
            "borderwidth": 0,
            "steps": [
                {"range": [0,  50], "color": "#FFEBEE"},
                {"range": [50, 80], "color": "#FFF8E1"},
                {"range": [80,100], "color": "#E8F5E9"},
            ],
            "threshold": {
                "line": {"color": C_INFO, "width": 2},
                "thickness": 0.65, "value": 80,
            },
        },
    ))
    fig.update_layout(height=230, paper_bgcolor="white",
                      margin=dict(t=30, b=10, l=20, r=20),
                      font=dict(family=FONT))
    return fig


def _nullity_hbar(df_meta: pd.DataFrame, layer_color: str, bg_color: str, title: str) -> go.Figure:
    df_s = df_meta.sort_values("nulos_pct", ascending=True)
    h    = max(340, len(df_s) * 26)

    # Color por severidad
    def _col(v):
        if v == 0:   return C_SUCCESS
        if v < 10:   return C_WARNING
        if v < 30:   return "#EF6C00"
        return C_DANGER

    colors = [_col(v) for v in df_s["nulos_pct"]]

    fig = go.Figure(go.Bar(
        x=df_s["nulos_pct"], y=df_s["columna"],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:.1f}%" for v in df_s["nulos_pct"]],
        textposition="outside",
        textfont=dict(size=10, family=FONT),
        hovertemplate="<b>%{y}</b><br>Nulidad: %{x:.2f}%<extra></extra>",
    ))
    # Línea de referencia al 10%
    fig.add_vline(x=10, line_dash="dot", line_color=C_WARNING, line_width=1.5,
                  annotation_text="10% umbral", annotation_font=dict(size=9, color=C_WARNING))

    _apply_base(fig,
        title=dict(text=title, font=dict(size=13, color=C_TEXT, family=FONT), x=0),
        height=h,
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        margin=dict(l=170, r=60, t=50, b=30),
        yaxis=dict(categoryorder="total ascending", tickfont=dict(size=10), gridcolor="#F0F0F0"),
        xaxis=dict(title="% Nulos", range=[0, max(df_s["nulos_pct"].max() * 1.2, 12)],
                   gridcolor="#EEEEEE", tickfont=dict(size=10)),
    )
    return fig


def _donut_dtype(df_meta: pd.DataFrame, layer_color: str, bg: str, title: str) -> go.Figure:
    counts = df_meta["tipo_dato"].value_counts().reset_index()
    counts.columns = ["tipo_dato", "cantidad"]
    palette = [layer_color, "#78909C", "#AED6F1", "#A9DFBF", "#F9E79F", "#FADBD8"]
    fig = go.Figure(go.Pie(
        labels=counts["tipo_dato"], values=counts["cantidad"],
        hole=0.55,
        marker=dict(colors=palette[:len(counts)], line=dict(color="white", width=2)),
        textinfo="percent+label",
        textfont=dict(size=11, family=FONT),
        hovertemplate="<b>%{label}</b><br>%{value} campos (%{percent})<extra></extra>",
    ))
    _apply_base(fig,
        title=dict(text=title, font=dict(size=13, color=C_TEXT, family=FONT), x=0),
        height=260,
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        showlegend=True,
        legend=dict(orientation="v", x=1.0, y=0.5, font=dict(size=10)),
        margin=dict(t=50, b=20, l=10, r=10),
    )
    return fig


def _outlier_funnel(df_meta: pd.DataFrame, layer_color: str, bg: str) -> go.Figure | None:
    if "outliers_n" not in df_meta.columns:
        return None
    df_o = df_meta[df_meta["outliers_n"] > 0].sort_values("outliers_n", ascending=False)
    if df_o.empty:
        return None
    fig = go.Figure(go.Bar(
        x=df_o["columna"], y=df_o["outliers_n"],
        marker=dict(
            color=df_o["outliers_n"],
            colorscale=[[0, C_GOLD_MID], [0.5, C_WARNING], [1, C_DANGER]],
            showscale=True,
            colorbar=dict(title="N° Outliers", thickness=12),
        ),
        text=df_o["outliers_n"],
        textposition="outside",
        textfont=dict(size=10),
        hovertemplate="<b>%{x}</b><br>Outliers: %{y:,}<extra></extra>",
    ))
    _apply_base(fig,
        title="Outliers detectados por campo",
        height=300,
        paper_bgcolor=bg, plot_bgcolor=bg,
        xaxis=dict(tickangle=-30, tickfont=dict(size=9)),
        yaxis=dict(title="N° Outliers"),
        margin=dict(t=50, b=70, l=40, r=40),
    )
    return fig


def _cardinality_bar(df_meta: pd.DataFrame, layer_color: str, bg: str) -> go.Figure:
    df_s = df_meta.sort_values("unicos_n", ascending=False)
    total = df_meta["total_filas_dataset"].iloc[0] if "total_filas_dataset" in df_meta.columns else None
    pct   = (df_s["unicos_n"] / total * 100).round(1) if total else None

    fig = go.Figure(go.Bar(
        x=df_s["columna"], y=df_s["unicos_n"],
        marker=dict(color=layer_color, opacity=0.85, line=dict(width=0)),
        text=[f"{v:,}" for v in df_s["unicos_n"]],
        textposition="outside",
        textfont=dict(size=9),
        hovertemplate="<b>%{x}</b><br>Valores únicos: %{y:,}<extra></extra>",
    ))
    _apply_base(fig,
        title="Cardinalidad por campo (valores únicos)",
        height=300,
        paper_bgcolor=bg, plot_bgcolor=bg,
        xaxis=dict(tickangle=-30, tickfont=dict(size=9)),
        yaxis=dict(title="Valores únicos"),
        margin=dict(t=50, b=80, l=40, r=20),
    )
    return fig


def _corr_heatmap(df_data: pd.DataFrame, title: str, bg: str = "white") -> go.Figure | None:
    numeric = df_data.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return None
    if numeric.shape[1] > 22:
        numeric = numeric.iloc[:, :22]
    corr = numeric.corr()
    n    = len(corr.columns)
    size = max(440, n * 52)

    # Mask upper triangle to keep clean
    mask  = np.triu(np.ones_like(corr.values, dtype=bool), k=1)
    zvals = corr.values.copy()
    zvals[mask] = None

    fig = go.Figure(go.Heatmap(
        z=zvals,
        x=corr.columns.tolist(),
        y=corr.columns.tolist(),
        colorscale=[
            [0.0,  "#C62828"], [0.25, "#EF9A9A"],
            [0.45, "#FAFAFA"], [0.55, "#FAFAFA"],
            [0.75, "#90CAF9"], [1.0,  "#1565C0"],
        ],
        zmid=0, zmin=-1, zmax=1,
        colorbar=dict(
            title=dict(text="r", font=dict(size=11)),
            thickness=14, len=0.8,
            tickfont=dict(size=10),
        ),
        text=np.where(mask, "", np.round(corr.values, 2)).tolist(),
        texttemplate="%{text}",
        textfont=dict(size=9),
        hoverongaps=False,
        hovertemplate="<b>%{x}</b> × <b>%{y}</b><br>r = %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=C_TEXT, family=FONT), x=0),
        height=size, width=size,
        paper_bgcolor=bg, plot_bgcolor=bg,
        font=dict(family=FONT, size=11),
        xaxis=dict(tickangle=-45, tickfont=dict(size=9), side="bottom"),
        yaxis=dict(tickfont=dict(size=9), autorange="reversed"),
        margin=dict(l=130, b=130, t=60, r=60),
    )
    return fig


def _nullity_treemap(df_meta: pd.DataFrame, layer_color: str, title: str) -> go.Figure | None:
    if "nulos_pct" not in df_meta.columns or "unicos_n" not in df_meta.columns:
        return None
    df = df_meta[["columna", "nulos_pct", "unicos_n"]].copy()
    df["completitud"] = (100 - df["nulos_pct"]).clip(0, 100)
    df["label"] = df["columna"] + "<br>" + df["completitud"].round(1).astype(str) + "% completo"
    fig = px.treemap(
        df, path=["columna"], values="unicos_n",
        color="completitud",
        color_continuous_scale=[[0, C_DANGER], [0.5, C_WARNING], [1, C_SUCCESS]],
        range_color=[0, 100],
        hover_data={"nulos_pct": ":.1f"},
        labels={"completitud": "% Completo", "nulos_pct": "% Nulos"},
        title=title,
    )
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>%{value:,} únicos",
        textfont=dict(size=11, family=FONT),
    )
    fig.update_layout(
        height=360, paper_bgcolor="white",
        margin=dict(t=50, b=10, l=10, r=10),
        font=dict(family=FONT),
        coloraxis_colorbar=dict(title="% Completo", thickness=12),
    )
    return fig


def _completeness_radar(df_bronze: pd.DataFrame, df_silver: pd.DataFrame) -> go.Figure | None:
    """Radar de completitud (1 - nulos_pct) para campos comunes."""
    common = sorted(set(df_bronze["columna"]) & set(df_silver["columna"]))
    if len(common) < 3:
        return None
    # Limitar a 16 campos para legibilidad
    common = common[:16]

    def _completeness(df, cols):
        sub = df[df["columna"].isin(cols)].set_index("columna")["nulos_pct"].reindex(cols).fillna(0)
        return (100 - sub).clip(0, 100).tolist()

    b_vals = _completeness(df_bronze, common)
    s_vals = _completeness(df_silver, common)

    fig = go.Figure()
    for vals, name, color, fill in [
        (b_vals, "Bronze", C_BRONZE, "rgba(181,101,29,.18)"),
        (s_vals, "Silver", C_SILVER, "rgba(84,110,122,.20)"),
    ]:
        theta = common + [common[0]]
        r     = vals + [vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=r, theta=theta, mode="lines+markers",
            fill="toself", fillcolor=fill,
            line=dict(color=color, width=2.5),
            marker=dict(size=5),
            name=name,
        ))
    fig.update_layout(
        polar=dict(
            bgcolor="#FAFAFA",
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9),
                             gridcolor="#E0E0E0", linecolor="#BDBDBD"),
            angularaxis=dict(tickfont=dict(size=9.5, family=FONT), gridcolor="#E8E8E8"),
        ),
        title=dict(text="Completitud por campo — Bronze vs Silver",
                   font=dict(size=13, color=C_TEXT, family=FONT), x=0),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, font=dict(size=11)),
        paper_bgcolor="white", margin=dict(t=60, b=60, l=30, r=30),
        height=420, font=dict(family=FONT),
    )
    return fig


def _improvement_waterfall(df_bronze: pd.DataFrame, df_silver: pd.DataFrame) -> go.Figure | None:
    common = sorted(set(df_bronze["columna"]) & set(df_silver["columna"]))
    if not common:
        return None
    b = df_bronze[df_bronze["columna"].isin(common)][["columna","nulos_pct"]].rename(columns={"nulos_pct":"b"})
    s = df_silver[df_silver["columna"].isin(common)][["columna","nulos_pct"]].rename(columns={"nulos_pct":"s"})
    m = b.merge(s, on="columna")
    m["delta"] = m["b"] - m["s"]
    m = m.sort_values("delta", ascending=False).head(18)

    colors = [C_SUCCESS if v > 0 else (C_MUTED if v == 0 else C_DANGER) for v in m["delta"]]
    fig = go.Figure(go.Bar(
        x=m["columna"], y=m["delta"],
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:+.1f}%" for v in m["delta"]],
        textposition="outside",
        textfont=dict(size=9.5),
        hovertemplate="<b>%{x}</b><br>Mejora: %{y:+.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="solid", line_color=C_BORDER, line_width=1)
    _apply_base(fig,
        title="Reducción de Nulidad por Campo (Bronze → Silver)",
        height=320,
        xaxis=dict(tickangle=-35, tickfont=dict(size=9)),
        yaxis=dict(title="Δ Nulidad (pp)", zeroline=True, zerolinecolor=C_BORDER),
        margin=dict(t=55, b=80, l=50, r=20),
    )
    return fig


def _null_scatter_b_vs_s(df_bronze: pd.DataFrame, df_silver: pd.DataFrame) -> go.Figure | None:
    common = sorted(set(df_bronze["columna"]) & set(df_silver["columna"]))
    if len(common) < 2:
        return None
    b = df_bronze[df_bronze["columna"].isin(common)][["columna","nulos_pct"]].rename(columns={"nulos_pct":"Bronze"})
    s = df_silver[df_silver["columna"].isin(common)][["columna","nulos_pct"]].rename(columns={"nulos_pct":"Silver"})
    df = b.merge(s, on="columna")
    df["mejora"] = df["Bronze"] - df["Silver"]

    fig = px.scatter(
        df, x="Bronze", y="Silver", text="columna",
        color="mejora",
        color_continuous_scale=[[0, C_DANGER], [0.5, "#BDBDBD"], [1, C_SUCCESS]],
        size=df["mejora"].abs().clip(lower=1) + 2,
        labels={"Bronze": "Nulidad en Bronze (%)", "Silver": "Nulidad en Silver (%)"},
        title="Bronze vs Silver: Nulidad por campo (scatter)",
        hover_data={"mejora": ":.2f"},
    )
    mx = max(df["Bronze"].max(), df["Silver"].max()) * 1.1
    fig.add_trace(go.Scatter(
        x=[0, mx], y=[0, mx], mode="lines", name="Sin cambio",
        line=dict(dash="dot", color=C_MUTED, width=1.5),
    ))
    fig.update_traces(textposition="top center", textfont=dict(size=8), selector=dict(mode="markers+text"))
    _apply_base(fig,
        height=420,
        coloraxis_colorbar=dict(title="Mejora (pp)", thickness=12),
        margin=dict(t=55, b=40, l=60, r=60),
    )
    return fig


# ═══════════════════════════════════════════════════════════════
# HELPERS HTML
# ═══════════════════════════════════════════════════════════════

def _section(title: str, sub: str = ""):
    st.subheader(title)
    if sub:
        st.caption(sub)


def _insight(text: str):
    # Strip basic HTML tags for plain text rendering
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    st.info(clean)


def _detail_table(df_meta: pd.DataFrame):
    cols = [c for c in ["columna", "tipo_dato", "nulos_n", "nulos_pct", "unicos_n", "outliers_n"] if c in df_meta.columns]
    st.dataframe(
        df_meta[cols].sort_values("nulos_pct", ascending=False).reset_index(drop=True),
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════
# SECCIÓN BRONZE
# ═══════════════════════════════════════════════════════════════

def _render_bronze(df: pd.DataFrame):
    st.markdown("## 🟤 Capa Bronze — CSV Original")
    st.caption("Estado crudo de los datos antes de cualquier transformación.")

    total_f  = df["total_filas_dataset"].iloc[0]
    total_d  = df["duplicados_dataset"].iloc[0]
    score    = quality_score(df)
    null_avg = df["nulos_pct"].mean() if "nulos_pct" in df.columns else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total registros",   f"{total_f:,}")
    m2.metric("Duplicados",         f"{total_d:,}")
    m3.metric("Campos en schema",   f"{len(df):,}")
    m4.metric("Nulidad promedio",   f"{null_avg:.1f}%")
    m5.metric("Score calidad",      f"{score:.1f}%",  delta="≥80% meta", delta_color="normal" if score >= 80 else "inverse")

    st.info(
        f"El dataset Bronze contiene {total_f:,} registros con {total_d:,} duplicados. "
        f"Nulidad promedio: {null_avg:.1f}% — los campos con mayor nulidad serán limpiados en Silver."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Score de Calidad")
        st.caption("Ref: 80% = umbral aceptable (línea azul)")
        st.plotly_chart(_gauge(score, "Bronze", C_BRONZE, C_BRONZE_LIGHT), use_container_width=True)
    with c2:
        st.subheader("Tipos de Dato")
        st.caption("Composición del schema por tipo")
        st.plotly_chart(_donut_dtype(df, C_BRONZE, C_BRONZE_LIGHT, ""), use_container_width=True)

    st.subheader("Nulidad por Campo")
    st.caption("Campos ordenados de menor a mayor nulidad. Umbral recomendado: 10% (línea naranja).")
    st.plotly_chart(_nullity_hbar(df, C_BRONZE, C_BRONZE_LIGHT, ""), use_container_width=True)

    st.subheader("Mapa de Completitud")
    st.caption("Área proporcional a la cardinalidad; color = % completitud (verde = completo, rojo = nulo).")
    fig_tree = _nullity_treemap(df, C_BRONZE, "Completitud y cardinalidad — Bronze")
    if fig_tree:
        st.plotly_chart(fig_tree, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Outliers")
        st.caption("Campos con anomalías detectadas (IQR).")
        fig_out = _outlier_funnel(df, C_BRONZE, C_BRONZE_LIGHT)
        if fig_out:
            st.plotly_chart(fig_out, use_container_width=True)
        else:
            st.success("✅ No se detectaron outliers en Bronze.")
    with c4:
        st.subheader("Cardinalidad")
        st.caption("Valores únicos por campo.")
        st.plotly_chart(_cardinality_bar(df, C_BRONZE, C_BRONZE_LIGHT), use_container_width=True)

    st.subheader("Detalle por Campo")
    _detail_table(df)


# ═══════════════════════════════════════════════════════════════
# SECCIÓN SILVER
# ═══════════════════════════════════════════════════════════════

def _render_silver(df: pd.DataFrame, df_bronze):
    st.markdown("## 🔘 Capa Silver — Parquet Limpio")
    st.caption("Tras deduplicación, normalización y limpieza de nulos críticos.")

    total_s  = df["total_filas_dataset"].iloc[0]
    score_s  = quality_score(df)
    null_avg = df["nulos_pct"].mean() if "nulos_pct" in df.columns else 0

    reduction = ""
    if df_bronze is not None:
        total_f   = df_bronze["total_filas_dataset"].iloc[0]
        reduction = f"{((total_f - total_s)/total_f)*100:.1f}%"

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Registros únicos",  f"{total_s:,}",  delta=f"-{reduction} vs Bronze" if reduction else None, delta_color="normal")
    m2.metric("Duplicados",         "0",              delta="Eliminados", delta_color="normal")
    m3.metric("Campos en schema",   f"{len(df):,}")
    m4.metric("Nulidad promedio",   f"{null_avg:.1f}%")
    m5.metric("Score calidad",      f"{score_s:.1f}%", delta="≥80% meta", delta_color="normal" if score_s >= 80 else "inverse")

    if reduction:
        st.info(
            f"Silver retiene {total_s:,} registros únicos (reducción del {reduction} respecto a Bronze). "
            f"Duplicados eliminados. Nulidad promedio: {null_avg:.1f}%."
        )

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Score de Calidad")
        st.caption("Ref: 80% = umbral aceptable")
        st.plotly_chart(_gauge(score_s, "Silver", C_SILVER, C_SILVER_LIGHT), use_container_width=True)
    with c2:
        st.subheader("Tipos de Dato")
        st.plotly_chart(_donut_dtype(df, C_SILVER, C_SILVER_LIGHT, ""), use_container_width=True)

    st.subheader("Nulidad por Campo")
    st.caption("Umbral recomendado: 10% (línea naranja).")
    st.plotly_chart(_nullity_hbar(df, C_SILVER, C_SILVER_LIGHT, ""), use_container_width=True)

    st.subheader("Mapa de Completitud")
    st.caption("Área proporcional a la cardinalidad; color = % completitud.")
    fig_tree = _nullity_treemap(df, C_SILVER, "Completitud y cardinalidad — Silver")
    if fig_tree:
        st.plotly_chart(fig_tree, use_container_width=True)

    st.subheader("Cardinalidad")
    st.plotly_chart(_cardinality_bar(df, C_SILVER, C_SILVER_LIGHT), use_container_width=True)

    st.subheader("Detalle por Campo")
    _detail_table(df)


# ═══════════════════════════════════════════════════════════════
# SECCIÓN GOLD
# ═══════════════════════════════════════════════════════════════

def _render_gold(df: pd.DataFrame):
    st.markdown("## 🥇 Capa Gold — Feature-Enriched")
    st.caption("Dataset enriquecido listo para análisis y modelos.")

    total_g  = len(df)
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    null_pct = df.isnull().mean().mean() * 100
    score_g  = max(0.0, 100.0 - null_pct)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Registros",          f"{total_g:,}")
    m2.metric("Campos numéricos",   f"{len(num_cols):,}")
    m3.metric("Campos categóricos", f"{len(cat_cols):,}")
    m4.metric("Nulidad promedio",   f"{null_pct:.2f}%")
    m5.metric("Score calidad",      f"{score_g:.1f}%", delta="≥80% meta", delta_color="normal" if score_g >= 80 else "inverse")

    st.info(
        f"Gold: {total_g:,} registros, {len(num_cols)} campos numéricos, "
        f"{len(cat_cols)} categóricos. Nulidad global: {null_pct:.2f}%."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Score de Calidad")
        st.caption("Ref: 80% = umbral aceptable")
        st.plotly_chart(_gauge(score_g, "Gold", C_GOLD, C_GOLD_LIGHT), use_container_width=True)
    with c2:
        st.subheader("Tipos de Dato")
        dtype_df = pd.DataFrame({"tipo_dato": df.dtypes.astype(str)}).reset_index()
        dtype_df.columns = ["columna", "tipo_dato"]
        st.plotly_chart(_donut_dtype(dtype_df, C_GOLD, C_GOLD_LIGHT, ""), use_container_width=True)

    nulls = df.isnull().mean().reset_index()
    nulls.columns = ["columna", "nulos_pct"]
    nulls["nulos_pct"] = (nulls["nulos_pct"] * 100).round(2)
    nulls["total_filas_dataset"] = total_g
    st.subheader("Nulidad por Campo (datos reales)")
    st.caption("Cada barra = % de filas nulas para ese campo.")
    st.plotly_chart(_nullity_hbar(nulls, C_GOLD, C_GOLD_LIGHT, ""), use_container_width=True)

    if num_cols:
        st.subheader("Estadísticas Descriptivas — Campos Numéricos")
        st.dataframe(df[num_cols].describe().T.round(3), use_container_width=True)

    st.subheader("Matriz de Correlación — Campos Numéricos")
    st.caption("Solo triángulo inferior. Rojo = correlación negativa, Azul = positiva.")
    fig_corr = _corr_heatmap(df, "Correlación — Gold", C_GOLD_LIGHT)
    if fig_corr:
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("No hay suficientes columnas numéricas para correlación.")


# ═══════════════════════════════════════════════════════════════
# SECCIÓN COMPARATIVA Bronze ↔ Silver
# ═══════════════════════════════════════════════════════════════

def _render_comparison(df_bronze: pd.DataFrame, df_silver: pd.DataFrame):
    st.markdown("## ⚖️ Bronze vs Silver — Evolución de la Calidad")

    bronze_cols = set(df_bronze["columna"])
    silver_cols = set(df_silver["columna"])
    common      = sorted(bronze_cols & silver_cols)
    score_b     = quality_score(df_bronze)
    score_s     = quality_score(df_silver)
    delta_score = score_s - score_b

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Score Bronze",    f"{score_b:.1f}%")
    m2.metric("Score Silver",    f"{score_s:.1f}%", delta=f"+{delta_score:.1f}pp", delta_color="normal")
    m3.metric("Campos comunes",  f"{len(common)}")
    m4.metric("Solo en Bronze",  f"{len(bronze_cols - silver_cols)}")
    m5.metric("Solo en Silver",  f"{len(silver_cols - bronze_cols)}")

    st.info(
        f"El score de calidad mejoró +{delta_score:.1f} puntos porcentuales de Bronze a Silver. "
        f"Existen {len(common)} campos comunes comparables entre ambas capas."
    )

    st.subheader("Radar de Completitud por Campo")
    st.caption("Muestra qué tan completo (sin nulos) está cada campo en cada capa.")
    fig_radar = _completeness_radar(df_bronze, df_silver)
    if fig_radar:
        st.plotly_chart(fig_radar, use_container_width=True)

    st.subheader("Reducción de Nulidad por Campo (Bronze → Silver)")
    st.caption("Verde = mejoró, rojo = empeoró. Top 18 campos.")
    fig_wf = _improvement_waterfall(df_bronze, df_silver)
    if fig_wf:
        st.plotly_chart(fig_wf, use_container_width=True)

    st.subheader("Scatter de Nulidad: Bronze (X) vs Silver (Y)")
    st.caption("Puntos bajo la diagonal = mejoraron. Tamaño proporcional a la mejora absoluta.")
    fig_sc = _null_scatter_b_vs_s(df_bronze, df_silver)
    if fig_sc:
        st.plotly_chart(fig_sc, use_container_width=True)

    st.divider()
    st.subheader("Comparativa Interactiva por Métrica")

    metric_options = {"% Nulidad": "nulos_pct", "N° Nulos": "nulos_n", "Cardinalidad": "unicos_n"}
    if "outliers_n" in df_bronze.columns:
        metric_options["N° Outliers"] = "outliers_n"

    col1, col2 = st.columns([1, 2])
    with col1:
        m_label   = st.selectbox("Métrica:", list(metric_options.keys()), key="comp_metric")
        metric    = metric_options[m_label]
        chart_typ = st.radio("Tipo:", ["Barras agrupadas", "Barras apiladas", "Scatter"], horizontal=True, key="comp_type")
    with col2:
        sel_cols = st.multiselect("Filtrar campos (vacío = todos):", common, default=[], key="comp_cols")

    use_cols  = sel_cols if sel_cols else common
    color_map = {"Bronze": C_BRONZE, "Silver": C_SILVER}

    df_b2 = df_bronze[df_bronze["columna"].isin(use_cols)][["columna", metric]].copy()
    df_b2["capa"] = "Bronze"
    df_s2 = df_silver[df_silver["columna"].isin(use_cols)][["columna", metric]].copy()
    df_s2["capa"] = "Silver"
    df_comp = pd.concat([df_b2, df_s2]).dropna(subset=[metric])

    if chart_typ == "Barras agrupadas":
        fig = px.bar(df_comp, x="columna", y=metric, color="capa", barmode="group",
                     color_discrete_map=color_map,
                     labels={"columna": "Campo", metric: m_label, "capa": "Capa"})
    elif chart_typ == "Barras apiladas":
        fig = px.bar(df_comp, x="columna", y=metric, color="capa", barmode="stack",
                     color_discrete_map=color_map,
                     labels={"columna": "Campo", metric: m_label, "capa": "Capa"})
    else:
        df_piv = df_comp.pivot(index="columna", columns="capa", values=metric).reset_index().dropna()
        if "Bronze" in df_piv and "Silver" in df_piv:
            fig = px.scatter(df_piv, x="Bronze", y="Silver", text="columna",
                             color_discrete_sequence=[C_BRONZE])
            mx = max(df_piv["Bronze"].max(), df_piv["Silver"].max()) * 1.1
            fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", name="Sin cambio",
                                     line=dict(dash="dot", color=C_MUTED, width=1.5)))
        else:
            fig = go.Figure()

    _apply_base(fig, xaxis=dict(tickangle=-35, tickfont=dict(size=9)), margin=dict(t=40, b=70, l=40, r=20))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Scoreboard por Campo")
    if "nulos_pct" in df_bronze.columns and "nulos_pct" in df_silver.columns:
        sb_b = df_bronze[["columna","nulos_pct","unicos_n"]].add_suffix("_b").rename(columns={"columna_b":"columna"})
        sb_s = df_silver[["columna","nulos_pct","unicos_n"]].add_suffix("_s").rename(columns={"columna_s":"columna"})
        sb   = sb_b.merge(sb_s, on="columna", how="inner")
        sb["Δ nulos_pct"] = (sb["nulos_pct_s"] - sb["nulos_pct_b"]).round(2)
        sb["Estado"] = sb["Δ nulos_pct"].apply(lambda x: "✅ Mejoró" if x < 0 else ("➡️ Igual" if x == 0 else "⚠️ Empeoró"))
        sb = sb.rename(columns={"nulos_pct_b": "Nulos% Bronze", "nulos_pct_s": "Nulos% Silver",
                                  "unicos_n_b": "Únicos Bronze",  "unicos_n_s": "Únicos Silver"})
        st.dataframe(
            sb[["columna","Nulos% Bronze","Nulos% Silver","Δ nulos_pct","Únicos Bronze","Únicos Silver","Estado"]]
            .sort_values("Δ nulos_pct"),
            use_container_width=True,
        )


# ═══════════════════════════════════════════════════════════════
# SECCIÓN CORRELACIONES
# ═══════════════════════════════════════════════════════════════

def _render_correlaciones(df_bronze, df_silver, df_gold):
    st.markdown("## 🔗 Matrices de Correlación por Capa")
    st.info(
        "Para Bronze y Silver se correlacionan las métricas de calidad "
        "(nulos, cardinalidad, outliers) de cada campo. "
        "Para Gold se correlacionan las variables numéricas reales del dataset enriquecido."
    )

    meta_cols = ["nulos_n", "nulos_pct", "unicos_n", "outliers_n"]

    tab_b, tab_s, tab_g = st.tabs(["🟤 Bronze", "🔘 Silver", "🥇 Gold"])

    with tab_b:
        st.subheader("Correlación de Métricas de Calidad — Bronze")
        st.caption("¿Campos con más nulos tienden a tener más outliers?")
        if df_bronze is not None:
            avail = [c for c in meta_cols if c in df_bronze.columns]
            if len(avail) >= 2:
                st.plotly_chart(_corr_heatmap(df_bronze[avail], "Correlación Métricas — Bronze", C_BRONZE_LIGHT) or go.Figure(),
                                use_container_width=True)
            else:
                st.info("Columnas insuficientes.")

    with tab_s:
        st.subheader("Correlación de Métricas de Calidad — Silver")
        st.caption("¿Se mantuvo la estructura de correlaciones tras la limpieza?")
        if df_silver is not None:
            avail = [c for c in meta_cols if c in df_silver.columns]
            if len(avail) >= 2:
                st.plotly_chart(_corr_heatmap(df_silver[avail], "Correlación Métricas — Silver", C_SILVER_LIGHT) or go.Figure(),
                                use_container_width=True)
            else:
                st.info("Columnas insuficientes.")

    with tab_g:
        st.subheader("Correlación de Variables Reales — Gold")
        st.caption("Selecciona los campos numéricos a incluir en la matriz.")
        if df_gold is not None:
            num_cols = df_gold.select_dtypes(include=[np.number]).columns.tolist()
            if len(num_cols) < 2:
                st.info("No hay suficientes columnas numéricas.")
            else:
                selected = st.multiselect(
                    "Campos (mín. 2, máx. recomendado 15):",
                    options=num_cols,
                    default=num_cols[:min(12, len(num_cols))],
                    key="corr_gold_sel",
                )
                if len(selected) >= 2:
                    fig = _corr_heatmap(df_gold[selected], "Correlación — Campos Seleccionados (Gold)", C_GOLD_LIGHT)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 Azul intenso > 0.7 = correlación positiva fuerte. Rojo intenso < -0.7 = negativa fuerte.")
                else:
                    st.warning("Selecciona al menos 2 campos.")
        else:
            st.warning("Datos Gold no disponibles.")


# ═══════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════

def render_quality_section():
    _inject_css()

    with st.spinner("Cargando datos de calidad…"):
        df_bronze = load_from_s3("metadata/healthcheck_report/")
        df_silver = load_from_s3("metadata/healthcheck_silver_parquet/")
        df_gold   = load_from_s3("gold/enhanced_for_streamlit_eda/")

    # ── Page header ──────────────────────────
    st.markdown("""
    <div class="qc-page-header">
        <h1>🔍 Control de Calidad — Arquitectura Medallion</h1>
        <p>
            Evidencia del estado de los datos en cada capa: <b>Bronze</b> (CSV raw) →
            <b>Silver</b> (Parquet limpio) → <b>Gold</b> (Feature-enriched para análisis).
            Usa las pestañas para explorar cada capa o compararlas interactivamente.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Score global (gauges compactos) ──────
    score_b = quality_score(df_bronze) if df_bronze is not None else 0.0
    score_s = quality_score(df_silver) if df_silver is not None else 0.0
    score_g = (100.0 - df_gold.isnull().mean().mean() * 100) if df_gold is not None else 0.0

    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(_gauge(score_b, "🟤 Bronze — Score Calidad", C_BRONZE, C_BRONZE_LIGHT),
                        use_container_width=True)
    with g2:
        st.plotly_chart(_gauge(score_s, "🔘 Silver — Score Calidad", C_SILVER, C_SILVER_LIGHT),
                        use_container_width=True)
    with g3:
        st.plotly_chart(_gauge(score_g, "🥇 Gold — Score Calidad", C_GOLD, C_GOLD_LIGHT),
                        use_container_width=True)

    st.divider()

    # ── Tabs principales ─────────────────────
    tab_b, tab_s, tab_g, tab_comp, tab_corr = st.tabs([
        "🟤 Bronze",
        "🔘 Silver",
        "🥇 Gold",
        "⚖️ Bronze vs Silver",
        "🔗 Correlaciones",
    ])

    with tab_b:
        if df_bronze is not None:
            _render_bronze(df_bronze)
        else:
            st.error("Reporte Bronze no encontrado en S3.")

    with tab_s:
        if df_silver is not None:
            _render_silver(df_silver, df_bronze)
        else:
            st.error("Reporte Silver no encontrado en S3.")

    with tab_g:
        if df_gold is not None:
            _render_gold(df_gold)
        else:
            st.error("Datos Gold no encontrados en S3.")

    with tab_comp:
        if df_bronze is not None and df_silver is not None:
            _render_comparison(df_bronze, df_silver)
        else:
            st.warning("Se necesitan Bronze y Silver para la comparativa.")

    with tab_corr:
        _render_correlaciones(df_bronze, df_silver, df_gold)
