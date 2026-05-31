import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Mapa de Quejas NYC",
    page_icon="🗺️",
    layout="wide",
)

# ── CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #1a1d27; border-right: 1px solid #2e3250; }
[data-testid="stSidebar"] * { color: #e0e4f0 !important; }
h1,h2,h3 { color: #e0e4f0 !important; }
.metric-card {
    background: #1e2235; border: 1px solid #2e3250;
    border-radius: 10px; padding: 14px 18px; text-align: center; color: #e0e4f0;
}
.metric-card .val { font-size: 1.8rem; font-weight: 700; color: #7c9cfc; }
.metric-card .lbl { font-size: 0.75rem; color: #8891b3; margin-top: 2px;
                    text-transform: uppercase; letter-spacing: .05em; }
.legend-card {
    background: #1e2235; border: 1px solid #2e3250;
    border-radius: 10px; padding: 16px 18px; color: #e0e4f0; margin-top: 0;
}
.legend-card h4 { margin: 0 0 10px 0; font-size: .8rem; color: #8891b3;
                  text-transform: uppercase; letter-spacing: .06em; }
.leg-row { display:flex; align-items:center; gap:8px; margin:5px 0; font-size:.82rem; }
.dot { width:11px; height:11px; border-radius:50%; flex-shrink:0; }
</style>
""", unsafe_allow_html=True)

# ── Colores por agencia ───────────────────────────────────────────────────
AGENCY_COLORS = {
    "NYPD":  "#7c9cfc",
    "DOB":   "#fc9c7c",
    "DHS":   "#7cfcbc",
    "HPD":   "#fc7cbc",
    "DOT":   "#fcdc7c",
    "DSNY":  "#bc9cfc",
    "DOHMH": "#7cdcfc",
    "DEP":   "#fc7c7c",
    "TLC":   "#9cfc7c",
    "DPR":   "#fca07c",
    "DCA":   "#7cbcfc",
    "DOE":   "#e07cfc",
}
DEFAULT_COLOR = "#aaaaaa"

BOROUGH_CENTERS = {
    "BRONX":         (40.845, -73.865),
    "BROOKLYN":      (40.650, -73.950),
    "MANHATTAN":     (40.775, -73.970),
    "QUEENS":        (40.730, -73.795),
    "STATEN ISLAND": (40.580, -74.150),
}

# ── Carga de datos ────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("gold.csv")
    return df.dropna(subset=["latitude", "longitude"])

df_all = load_data()

all_agencies = sorted(df_all["Agency"].unique())
all_boroughs = sorted(df_all["Borough"].unique())
all_ctypes   = sorted(df_all["Complaint Type"].unique())

# Mapa agencia → tipos de queja válidos (y viceversa)
agency_to_ctypes = (
    df_all.groupby("Agency")["Complaint Type"]
    .apply(lambda s: set(s.unique()))
    .to_dict()
)
ctype_to_agencies = (
    df_all.groupby("Complaint Type")["Agency"]
    .apply(lambda s: set(s.unique()))
    .to_dict()
)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗂️ Filtros")
    st.markdown("---")

    # Resultado / Cumplimiento
    target_map = {"Todos": None, "1 – Incumplió": 1, "0 – Cumplió": 0}
    target_sel = st.selectbox("Resultado", list(target_map.keys()))

    # Agencias — filtra los tipos disponibles
    sel_agencies = st.multiselect("Agencia", all_agencies, default=all_agencies)

    # Tipos de queja disponibles según agencias seleccionadas
    if sel_agencies:
        ctypes_disponibles = sorted(
            set().union(*[agency_to_ctypes.get(a, set()) for a in sel_agencies])
        )
    else:
        ctypes_disponibles = all_ctypes

    # Tipos de queja — filtra las agencias disponibles
    sel_ctypes = st.multiselect(
        "Tipo de queja",
        ctypes_disponibles,
        default=ctypes_disponibles,
    )

    # Agencias disponibles según tipos seleccionados (para info, no cambia el widget)
    if sel_ctypes:
        agencies_para_ctypes = sorted(
            set().union(*[ctype_to_agencies.get(c, set()) for c in sel_ctypes])
        )
        # Si el usuario ya limitó agencias, respetamos esa selección
        # Solo mostramos aviso si hay incompatibilidad
        incompatibles = [a for a in sel_agencies if a not in agencies_para_ctypes]
        if incompatibles:
            st.caption(f"⚠️ Sin datos para: {', '.join(incompatibles)} con los tipos seleccionados.")

    # Borough
    sel_borough = st.selectbox("Municipio", ["Todos"] + all_boroughs)

# ── Aplicar filtros ───────────────────────────────────────────────────────
df = df_all.copy()

if target_map[target_sel] is not None:
    df = df[df["target"] == target_map[target_sel]]

if sel_agencies:
    df = df[df["Agency"].isin(sel_agencies)]

if sel_ctypes:
    df = df[df["Complaint Type"].isin(sel_ctypes)]

borough_active = None if sel_borough == "Todos" else sel_borough
if borough_active:
    df = df[df["Borough"] == borough_active]

# ── Métricas ──────────────────────────────────────────────────────────────
st.markdown("## 🗺️ Mapa Geográfico de Quejas — Nueva York")

c1, c2, c3, c4 = st.columns(4)
total_pen = df[df["penalty_charged"] > 0]["penalty_charged"].sum()
pct_inc   = (df["target"] == 1).mean() * 100 if len(df) else 0

for col, val, lbl in [
    (c1, f"{len(df):,}",               "Incidentes"),
    (c2, f"${total_pen:,.0f}",         "Total Penalidad"),
    (c3, f"{pct_inc:.1f}%",            "Incumplieron"),
    (c4, str(df["Agency"].nunique()),   "Agencias activas"),
]:
    col.markdown(
        f"<div class='metric-card'><div class='val'>{val}</div>"
        f"<div class='lbl'>{lbl}</div></div>",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Mapa Plotly ───────────────────────────────────────────────────────────
BUBBLE_SIZE = 9

df = df.copy()
df["_color"]      = df["Agency"].map(AGENCY_COLORS).fillna(DEFAULT_COLOR)
df["_target_lbl"] = df["target"].map({1: "❌ Incumplió", 0: "✅ Cumplió"})
df["_pen_str"]    = df["penalty_charged"].apply(
    lambda x: f"${x:,.0f}" if x > 0 else "$0"
)

SYMBOL_MAP  = {0: "circle",  1: "circle"}
OPACITY_MAP = {0: 0.80,      1: 0.90}

traces = []

for agency in (sel_agencies or all_agencies):
    for target_val in [0, 1]:
        sub = df[(df["Agency"] == agency) & (df["target"] == target_val)]
        if sub.empty:
            continue
        color = AGENCY_COLORS.get(agency, DEFAULT_COLOR)

        hover = (
            "<b>" + sub["Complaint Type"] + "</b><br>" +
            "Agencia: <b>" + sub["Agency"] + "</b><br>" +
            "Municipio: " + sub["Borough"] + "<br>" +
            "Resultado: " + sub["_target_lbl"] + "<br>" +
            "Penalidad: <b>" + sub["_pen_str"] + "</b><br>" +
            "Días SLA: " + sub["sla_days"].round(2).astype(str) + "<br>" +
            "ZIP: " + sub["Incident Zip"].astype(str) +
            "<extra></extra>"
        )

        traces.append(go.Scattermap(
            lat=sub["latitude"],
            lon=sub["longitude"],
            mode="markers",
            marker=dict(
                size=BUBBLE_SIZE,
                symbol=SYMBOL_MAP[target_val],
                color=color,
                opacity=OPACITY_MAP[target_val],
            ),
            name=agency,
            hovertemplate=hover,
            legendgroup=agency,
            showlegend=(target_val == 0),
        ))

# Etiqueta de borough seleccionado
if borough_active and borough_active in BOROUGH_CENTERS:
    clat, clon = BOROUGH_CENTERS[borough_active]
    traces.append(go.Scattermap(
        lat=[clat], lon=[clon],
        mode="markers+text",
        marker=dict(size=1, color="rgba(0,0,0,0)"),
        text=[borough_active],
        textfont=dict(size=16, color="#7c9cfc"),
        textposition="middle center",
        showlegend=False,
        hoverinfo="skip",
    ))

# Centro y zoom del mapa
if borough_active and borough_active in BOROUGH_CENTERS:
    map_lat, map_lon = BOROUGH_CENTERS[borough_active]
    zoom = 12
else:
    map_lat, map_lon = 40.730, -73.935
    zoom = 10

layout = go.Layout(
    map=dict(
        style="carto-darkmatter",
        center=dict(lat=map_lat, lon=map_lon),
        zoom=zoom,
    ),
    legend=dict(
        title=dict(text="Agencia", font=dict(color="#8891b3", size=12)),
        bgcolor="#1e2235",
        bordercolor="#2e3250",
        borderwidth=1,
        font=dict(color="#e0e4f0", size=11),
        x=0.01, y=0.99,
        xanchor="left", yanchor="top",
    ),
    paper_bgcolor="#0f1117",
    plot_bgcolor="#0f1117",
    margin=dict(l=0, r=0, t=0, b=0),
    height=600,
)

fig = go.Figure(data=traces, layout=layout)

# ── Render ────────────────────────────────────────────────────────────────
col_map, col_legend = st.columns([4, 1])

with col_map:
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

with col_legend:
    # ── Leyenda de forma (cumplimiento) ──
    n_cumple   = len(df[df["target"] == 0])
    n_incumple = len(df[df["target"] == 1])
    shape_html = f"""
<div class='legend-card' style='margin-bottom:12px'>
  <h4>Forma · Resultado</h4>
  <div class='leg-row' style='margin:8px 0'>
    <svg width='14' height='14'>
      <circle cx='7' cy='7' r='6' fill='#e0e4f0' opacity='.9'/>
    </svg>
    <span style='font-size:.82rem;color:#e0e4f0;flex:1'>Cumplió</span>
    <span style='font-size:.75rem;color:#8891b3'>{n_cumple:,}</span>
  </div>
  <div class='leg-row' style='margin:8px 0'>
    <svg width='14' height='14'>
      <rect x='1' y='1' width='12' height='12' fill='#e0e4f0' opacity='.9' rx='1'/>
    </svg>
    <span style='font-size:.82rem;color:#e0e4f0;flex:1'>Incumplió</span>
    <span style='font-size:.75rem;color:#8891b3'>{n_incumple:,}</span>
  </div>
</div>
"""
    st.markdown(shape_html, unsafe_allow_html=True)

    # ── Leyenda de agencias ──
    agency_html = "<div class='legend-card'><h4>🏢 Agencias</h4>"
    for ag, col_hex in AGENCY_COLORS.items():
        if ag in (sel_agencies or all_agencies):
            cnt = len(df[df["Agency"] == ag])
            agency_html += f"""
<div class='leg-row'>
  <div class='dot' style='background:{col_hex}'></div>
  <span style='font-size:.8rem;color:#e0e4f0;flex:1'>{ag}</span>
  <span style='font-size:.75rem;color:#8891b3'>{cnt}</span>
</div>"""
    agency_html += "</div>"
    st.markdown(agency_html, unsafe_allow_html=True)

# ── Tabla de datos ────────────────────────────────────────────────────────
with st.expander("📋 Ver datos filtrados"):
    cols_show = ["Complaint Type", "Agency", "Borough", "Incident Zip",
                 "target", "penalty_charged", "sla_days"]
    st.dataframe(
        df[cols_show].rename(columns={
            "Complaint Type": "Tipo de Queja",
            "Agency":         "Agencia",
            "Borough":        "Municipio",
            "Incident Zip":   "ZIP",
            "target":         "Resultado",
            "penalty_charged":"Penalidad",
            "sla_days":       "Días SLA",
        }),
        use_container_width=True, height=300,
    )