import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np # Para cálculos numéricos
import requests # Para el GeoJSON

# --- RUTA DE LA CAPA GOLD ---
# ¡Asegúrate de que esta ruta coincida con la que usaste en el notebook de Glue!
PATH_GOLD_EDA = "s3://proyecto-ny311/gold/enhanced_for_streamlit_eda/"


@st.cache_data(ttl=3600, show_spinner="Cargando datos enriquecidos para EDA...")
def load_data_for_eda():
    """Carga los datos enriquecidos desde la capa Gold."""
    try:
        # Streamlit puede leer Parquet directamente desde S3 si la máquina tiene credenciales AWS configuradas
        df = pd.read_parquet(PATH_GOLD_EDA)
        
        # Convertir columnas de fecha que vienen como strings o con huso horario
        df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
        df['Closed Date'] = pd.to_datetime(df['Closed Date'], errors='coerce')
        df['created_date_only'] = pd.to_datetime(df['created_date_only'], errors='coerce')
        
        # Asegurarse de que las columnas categóricas sean de tipo string para Plotly
        str_cols = ['Complaint Type', 'Borough', 'created_day_of_week_name', 'Incident Zip', 'Community Board',
                    'City Council Districts', 'Police Precincts', 'Community Districts', 'Borough Boundaries',
                    'Park Facility Name', 'Agency', 'Agency Name', 'Location Type', 'Descriptor']
        for col_name in str_cols:
            if col_name in df.columns:
                df[col_name] = df[col_name].astype(str).replace('NAN', 'N/A').replace('NONE', 'N/A').replace('NULL', 'N/A')

        return df
    except Exception as e:
        st.error(f"Error al cargar los datos desde Gold: {e}. Asegúrate de que el job de Glue se ejecutó correctamente y el bucket S3 es accesible.")
        return pd.DataFrame() # Retorna un DataFrame vacío en caso de error


def render_dynamic_charts():
    """
    Renderiza gráficas dinámicas optimizadas para la "Ingeniería de la Atención",
    enfocadas en la probabilidad de incumplimiento de SLA.
    """
    
    st.header("Análisis Exploratorio: Riesgo de Incumplimiento de SLA en NYC 311")
    st.markdown("""
    Este dashboard interactivo explora los patrones de los incidentes del 311 de NYC con un enfoque
    en la **probabilidad de que una queja no sea resuelta dentro del tiempo esperado (SLA)** para su categoría.
    Utilizamos un umbral del percentil 75 del tiempo de resolución por tipo de queja para identificar el riesgo.
    """)

    df_raw = load_data_for_eda()
    
    if df_raw.empty:
        st.warning("No hay datos disponibles para el EDA. Por favor, asegúrate de que el notebook de Glue haya procesado y guardado los datos en la capa Gold.")
        return
    
    # Filtrar solo registros resueltos con SLA calculado para la mayoría de los análisis
    # Pero para algunos gráficos (ej. Total Incidentes), usamos todo el df_raw
    df_work = df_raw[df_raw['resolution_time_days'].notna() & df_raw['p75_resolution_time_days'].notna()].copy()
    
    if df_work.empty:
        st.warning("No hay suficientes datos resueltos con umbrales de SLA para realizar los análisis. Esto podría deberse a un dataset muy pequeño o a problemas en el cálculo de SLA en la capa Gold.")
        return

    # Mapeo de columnas (ya pre-calculadas en la capa Gold)
    # Se usan los nombres de columnas de la capa Gold para evitar next((col for col...))
    created_date_col = 'Created Date'
    created_date_only_col = 'created_date_only'
    created_day_of_week_name_col = 'created_day_of_week_name'
    created_hour_col = 'created_hour'
    complaint_col = 'Complaint Type'
    borough_col = 'Borough'
    is_sla_non_compliant_col = 'is_sla_non_compliant'
    resolution_time_col = 'resolution_time_days'
    p75_resolution_time_col = 'p75_resolution_time_days'
    community_board_col = 'Community Board'
    lat_col = 'latitude'
    lon_col = 'longitude'
    agency_col = 'Agency Name'
    channel_col = 'Open Data Channel Type'

    # PALETA DE COLORES SELECTIVA Y PRINCIPIOS DE "INGENIERÍA DE LA ATENCIÓN"
    COLOR_FOCO = "#C0292B"       # Rojo estratégico para anomalías / riesgo alto de incumplimiento
    COLOR_NEUTRO = "#718096"     # Gris medio para contexto histórico o categorías de bajo riesgo
    COLOR_ALERTA = "#FFCA28"     # Amarillo/Naranja para advertencia, riesgo medio
    COLOR_OK = "#00C853"         # Verde para cumplimiento, buen rendimiento
    COLOR_FONDO_LIGERO = "white"
    
    # Configuración base reutilizable para los ejes
    EJE_BASE_DICT = dict(
        showline=True,
        linewidth=1.2,
        linecolor="rgba(74, 85, 104, 0.5)",
        ticks="outside",
        tickfont=dict(color="#2D3748", size=10),
        title_font=dict(color="#2D3748", size=12, family="Arial")
    )

    # ======================================================================
    # KPIs PRINCIPALES DE SLA
    # ======================================================================
    st.markdown("---")
    st.subheader("📊 Resumen General de Incumplimiento de SLA")
    
    total_incidents_raw = len(df_raw) # Total de incidentes desde la capa Gold (incluye no resueltos)
    total_resolved = len(df_work)     # Solo incidentes con tiempo de resolución válido
    total_non_compliant = df_work[df_work[is_sla_non_compliant_col] == 1].shape[0]
    non_compliant_rate = (total_non_compliant / total_resolved) if total_resolved > 0 else 0

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    col_kpi1.metric("Total Incidentes (Dataset)", f"{total_incidents_raw:,}")
    col_kpi2.metric("Incidentes Resueltos con SLA", f"{total_resolved:,}")
    col_kpi3.metric("Incidentes Fuera de SLA", f"{total_non_compliant:,}")
    col_kpi4.metric("Tasa de Incumplimiento SLA", f"{non_compliant_rate:.2%}")
    st.markdown("---")


    # ======================================================================
    # DISTRIBUCIÓN POR CATEGORÍA Y BOROUGH (Enfoque en Incumplimiento SLA)
    # ======================================================================
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Top 10 Categorías con Mayor Riesgo de Incumplimiento de SLA")
        st.write("Identifica las quejas que más frecuentemente superan su tiempo esperado de resolución.")
        if complaint_col and is_sla_non_compliant_col:
            df_sla_rate_complaint = df_work.groupby(complaint_col)[is_sla_non_compliant_col].mean().reset_index()
            df_sla_rate_complaint.columns = ['Tipo', 'Tasa de Incumplimiento']
            df_sla_rate_complaint = df_sla_rate_complaint.sort_values('Tasa de Incumplimiento', ascending=False).head(10) # Top 10
            df_sla_rate_complaint = df_sla_rate_complaint.sort_values('Tasa de Incumplimiento', ascending=True) # Orden ascendente para que el top quede arriba en el gráfico de barras

            idx_max = df_sla_rate_complaint['Tasa de Incumplimiento'].idxmax()
            colores_quejas = [COLOR_NEUTRO] * len(df_sla_rate_complaint)
            colores_quejas[idx_max] = COLOR_FOCO # Resaltar la categoría con mayor tasa

            fig = px.bar(df_sla_rate_complaint, x='Tasa de Incumplimiento', y='Tipo', orientation='h')
            fig.update_traces(marker_color=colores_quejas, opacity=0.85)

            fig.add_annotation(
                x=df_sla_rate_complaint.loc[idx_max, 'Tasa de Incumplimiento'],
                y=df_sla_rate_complaint.loc[idx_max, 'Tipo'],
                text=f"Mayor riesgo: {df_sla_rate_complaint.loc[idx_max, 'Tasa de Incumplimiento']:.1%}",
                showarrow=True,
                arrowhead=3,
                ax=40, ay=0,
                font=dict(color=COLOR_FOCO, size=11, weight='bold'),
                arrowcolor=COLOR_FOCO,
                bgcolor="rgba(255,255,255,0.8)"
            )
            
            fig.update_layout(
                showlegend=False, plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(**EJE_BASE_DICT, showgrid=False, tickformat=".0%", title_text="Tasa de Incumplimiento de SLA"),
                yaxis=dict(**EJE_BASE_DICT, title_text="Tipo de Incidente", categoryorder='total ascending')
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Tasa de Incumplimiento de SLA por Distrito (Borough)")
        st.write("¿Qué boroughs muestran mayor dificultad para cumplir con los SLAs?")
        if borough_col and is_sla_non_compliant_col:
            borough_sla_rate = df_work.groupby(borough_col)[is_sla_non_compliant_col].mean().reset_index()
            borough_sla_rate.columns = ['Distrito', 'Tasa de Incumplimiento']
            
            borough_sla_rate = borough_sla_rate.sort_values(by='Tasa de Incumplimiento', ascending=True)
            
            idx_max_borough = borough_sla_rate['Tasa de Incumplimiento'].idxmax()
            colores_distritos = [COLOR_NEUTRO] * len(borough_sla_rate)
            colores_distritos[idx_max_borough] = COLOR_FOCO # Resaltar el borough con la tasa más alta
            
            fig = px.bar(borough_sla_rate, x='Tasa de Incumplimiento', y='Distrito', orientation='h')
            fig.update_traces(marker_color=colores_distritos, opacity=0.85)
            
            fig.update_layout(
                showlegend=False, plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(**EJE_BASE_DICT, showgrid=False, tickformat=".0%", title_text="Tasa de Incumplimiento de SLA"),
                yaxis=dict(**EJE_BASE_DICT, title_text="Distrito (Borough)")
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")


    # ======================================================================
    # EVOLUCIÓN TEMPORAL DE LA TASA DE INCUMPLIMIENTO DE SLA
    # ======================================================================
    if created_date_only_col and is_sla_non_compliant_col:
        st.subheader("📈 Evolución Temporal de la Tasa de Incumplimiento de SLA")
        st.write("Analiza cómo varía el riesgo de incumplimiento a lo largo del tiempo para detectar tendencias o anomalías.")
        
        df_daily_sla = df_work.groupby(created_date_only_col)[is_sla_non_compliant_col].mean().reset_index()
        df_daily_sla.columns = ['Fecha', 'Tasa de Incumplimiento']
        df_daily_sla['Fecha'] = pd.to_datetime(df_daily_sla['Fecha']) # Asegurar tipo datetime

        # Identificar el punto de quiebre o anomalía (ej. donde la tasa es más alta)
        idx_max = df_daily_sla['Tasa de Incumplimiento'].idxmax()
        row_max = df_daily_sla.loc[idx_max]

        fig = px.line(df_daily_sla, x='Fecha', y='Tasa de Incumplimiento')
        fig.update_traces(line_color=COLOR_NEUTRO, line_width=2, name="Tendencia")
        
        # Resaltar el pico máximo de incumplimiento con COLOR_FOCO
        fig.add_trace(go.Scatter(
            x=[row_max['Fecha']], 
            y=[row_max['Tasa de Incumplimiento']],
            mode='markers+text',
            marker=dict(color=COLOR_FOCO, size=12, line=dict(width=2, color='white')),
            text=[f"Pico SLA: {row_max['Tasa de Incumplimiento']:.1%}"],
            textposition="top center",
            textfont=dict(color=COLOR_FOCO, size=12, weight='bold'),
            name="Máximo Incumplimiento"
        ))
        
        fig.update_layout(
            showlegend=False, plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
            xaxis=dict(**EJE_BASE_DICT, showgrid=False, title_text="Línea de Tiempo"),
            yaxis=dict(**EJE_BASE_DICT, showgrid=True, gridcolor="rgba(0,0,0,0.08)", tickformat=".0%", title_text="Tasa Diaria de Incumplimiento")
        )
        st.plotly_chart(fig, use_container_width=True)

        # ======================================================================
        # DISTRIBUCIÓN TEMPORAL: DÍA DE LA SEMANA Y HORA DEL DÍA
        # ======================================================================
        st.subheader("⏰ Patrones de Incumplimiento de SLA por Día de la Semana y Hora del Día")
        st.write("Identifica los días de la semana y las horas del día con mayor riesgo de no cumplir el SLA. Ayuda a programar recursos.")

        weekday_sla_dist = (
            df_work.groupby(created_day_of_week_name_col)[is_sla_non_compliant_col].mean().reset_index(name="Tasa de Incumplimiento")
        )
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday_sla_dist[created_day_of_week_name_col] = pd.Categorical(weekday_sla_dist[created_day_of_week_name_col], categories=weekday_order, ordered=True)
        weekday_sla_dist = weekday_sla_dist.sort_values(created_day_of_week_name_col)

        hour_sla_dist = (
            df_work.groupby(created_hour_col)[is_sla_non_compliant_col].mean().reset_index(name="Tasa de Incumplimiento")
            .sort_values(created_hour_col)
        )

        row_time_1, row_time_2 = st.columns(2)

        with row_time_1:
            st.markdown("##### Por Día de la Semana")
            # Resaltar el día con la tasa más alta
            idx_max_weekday = weekday_sla_dist['Tasa de Incumplimiento'].idxmax()
            colores_weekday = [COLOR_NEUTRO] * len(weekday_sla_dist)
            colores_weekday[idx_max_weekday] = COLOR_FOCO # Resaltar con COLOR_FOCO
            
            fig_weekday = px.bar(weekday_sla_dist, x="Tasa de Incumplimiento", y=created_day_of_week_name_col, orientation="h")
            fig_weekday.update_traces(marker_color=colores_weekday, opacity=0.85)
            fig_weekday.update_layout(
                showlegend=False, plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis={**EJE_BASE_DICT, "showgrid": False, "tickformat": ".0%", "title_text": "Tasa de Incumplimiento"},
                yaxis={**EJE_BASE_DICT, "title_text": "Día de la Semana"},
                height=350
            )
            st.plotly_chart(fig_weekday, use_container_width=True)

        with row_time_2:
            st.markdown("##### Por Hora del Día")
            # Resaltar la hora con la tasa más alta
            idx_max_hour = hour_sla_dist['Tasa de Incumplimiento'].idxmax()
            colores_hour = [COLOR_NEUTRO] * len(hour_sla_dist)
            colores_hour[idx_max_hour] = COLOR_FOCO # Resaltar con COLOR_FOCO
            
            fig_hour = px.bar(hour_sla_dist, x=created_hour_col, y="Tasa de Incumplimiento")
            fig_hour.update_traces(marker_color=colores_hour, opacity=0.85)
            fig_hour.update_layout(
                showlegend=False, plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis={**EJE_BASE_DICT, "title_text": "Hora del Día"},
                yaxis={**EJE_BASE_DICT, "tickformat": ".0%", "title_text": "Tasa de Incumplimiento"},
                height=350
            )
            st.plotly_chart(fig_hour, use_container_width=True)

    st.markdown("---")


    # ======================================================================
    # MAPA DE CALOR GEOGRÁFICO POR TASA DE INCUMPLIMIENTO DE SLA (Community Districts)
    # ======================================================================
    st.header("🗺️ Concentración Geográfica del Riesgo de Incumplimiento de SLA")
    st.write("Identifica las áreas (Community Districts) con la mayor tasa de incumplimiento de SLA. Las zonas **rojas** demandan atención inmediata.")

    if not lat_col or not lon_col:
        st.info("No hay columnas de latitud/longitud disponibles para este mapa.")
    elif not community_board_col:
        st.info(f"No se encontró la columna '{community_board_col}' en el dataset.")
    else:
        # Colores para el mapa de calor de incumplimiento de SLA (escala de verde a rojo)
        COLORSCALE_SLA = [
            [0.0, COLOR_OK],    # Verde para baja tasa de incumplimiento
            [0.5, COLOR_ALERTA], # Amarillo para tasa media (punto de quiebre)
            [1.0, COLOR_FOCO]   # Rojo para alta tasa de incumplimiento (anomalía, foco)
        ]

        # Funciones y diccionarios para el mapa (incluidos aquí para auto-contención)
        BORO_CODE = {
            "MANHATTAN": 1, "MN": 1, "NEW YORK": 1,
            "BRONX": 2,     "BX": 2,
            "BROOKLYN": 3,  "BK": 3,
            "QUEENS": 4,    "QN": 4, "QS": 4,
            "STATEN ISLAND": 5, "SI": 5,
        }
        BORO_NAMES = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}

        def parse_borocd(val):
            """Convierte '01 BROOKLYN' → 301, '12 QUEENS' → 412, etc. Y maneja 'N/A'"""
            try:
                if val == 'N/A' or pd.isna(val):
                    return None
                parts = str(val).strip().split()
                if len(parts) < 2: # Puede ser solo un número o un nombre
                    if str(val).isdigit(): # Si es solo un número, asumimos que es el CD sin Borough
                         # Esto es una simplificación, idealmente se necesita el Borough
                         # Aquí asignaremos al borough 1 (Manhattan) por defecto si no hay info
                        return 100 + int(val) 
                    return None
                num = int(parts[0])
                boro_str = " ".join(parts[1:]).upper()
                code = BORO_CODE.get(boro_str)
                if code is None: # Intento de búsqueda parcial o por sinónimos
                    for key, v in BORO_CODE.items():
                        if boro_str in key or key in boro_str:
                            code = v
                            break
                if code is None:
                    return None
                return code * 100 + num
            except Exception:
                return None

        df_cd_map_source = df_work.dropna(subset=[community_board_col, is_sla_non_compliant_col]).copy()
        df_cd_map_source['borocd'] = df_cd_map_source[community_board_col].apply(parse_borocd)
        df_cd_map_source = df_cd_map_source.dropna(subset=['borocd'])
        df_cd_map_source['borocd'] = df_cd_map_source['borocd'].astype(int)
        df_cd_map_source['boro_code'] = (df_cd_map_source['borocd'] // 100).astype(int)

        # Tasa de incumplimiento por Community District (usando df_cd_map_source para asegurar que tiene borocd)
        df_sla_cd_rate = df_cd_map_source.groupby(['borocd', 'boro_code'])[is_sla_non_compliant_col].mean().reset_index(name='tasa_incumplimiento')

        # Descarga del GeoJSON (tu URL original)
        GEOJSON_CD_URL = (
            "https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/"
            "NYC_Community_Districts/FeatureServer/0/query"
            "?where=1%3D1&outFields=BoroCD&outSR=4326&f=geojson"
        )

        @st.cache_data(ttl=7200, show_spinner="Cargando límites de Community Districts...")
        def fetch_cd_geojson():
            try:
                r = requests.get(GEOJSON_CD_URL, timeout=25)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("features"):
                        return data
            except Exception:
                pass
            return None

        geojson_cd = fetch_cd_geojson()

        if not geojson_cd:
            st.caption("⚠️ GeoJSON de Community Districts no disponible. No se puede mostrar el mapa coroplético. Asegúrate de tener conexión a internet.")
        else:
            fig_cd = go.Figure(go.Choroplethmapbox(
                geojson=geojson_cd,
                locations=df_sla_cd_rate['borocd'],
                z=df_sla_cd_rate['tasa_incumplimiento'],
                featureidkey="properties.BoroCD",
                colorscale=COLORSCALE_SLA,
                zmin=0, # Escala de 0 a 1 (0% a 100% de incumplimiento)
                zmax=1,
                marker_opacity=0.8,
                marker_line_width=1,
                marker_line_color="rgba(255,255,255,0.4)",
                hovertemplate=(
                    "<b>Distrito: %{location}</b><br>"
                    "Tasa de Incumplimiento SLA: <b>%{z:.1%}</b><extra></extra>"
                ),
                colorbar=dict(
                    title="Tasa Incumplimiento SLA",
                    titleside="right",
                    bgcolor="rgba(255,255,255,0.8)",
                    tickformat=".0%"
                )
            ))

            fig_cd.update_layout(
                mapbox=dict(
                    style="carto-positron",
                    center=dict(lat=40.7128, lon=-74.0060),
                    zoom=9.5
                ),
                margin=dict(t=10, b=10, l=10, r=10),
                height=660,
                showlegend=False,
                paper_bgcolor="white"
            )
            st.plotly_chart(fig_cd, use_container_width=True)

            st.markdown(
                f"""
                <div style="padding:12px 16px; border-left:4px solid #4A5568;
                            background:rgba(0,0,0,0.04); border-radius:4px; margin-bottom:18px;">
                    <span style="color:#2D3748; font-size:12px; font-weight:700; letter-spacing:1px;">LEYENDA</span><br><br>
                    <span style='color:{COLOR_OK};font-weight:600;'>🟢 Verde</span> = Baja tasa de incumplimiento de SLA<br>
                    <span style='color:{COLOR_ALERTA};font-weight:600;'>🟡 Amarillo</span> = Tasa media de incumplimiento de SLA<br>
                    <span style='color:{COLOR_FOCO};font-weight:600;'>🔴 Rojo</span> = Alta tasa de incumplimiento de SLA
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("---")


    # ======================================================================
    # ANÁLISIS POR AGENCIA Y CANAL (Incumplimiento SLA)
    # ======================================================================
    st.header("🏢 Impacto de Agencias y Canales en el Incumplimiento de SLA")
    st.write("¿Qué agencias y canales de reporte tienen mayor dificultad para cumplir con los SLAs? Esto puede guiar decisiones operativas.")

    if agency_col and channel_col and is_sla_non_compliant_col:
        col_agency_sla, col_channel_sla = st.columns(2)

        with col_agency_sla:
            st.markdown("##### Tasa de Incumplimiento por Agencia")
            df_agency_sla = df_work.groupby(agency_col)[is_sla_non_compliant_col].mean().reset_index(name='Tasa de Incumplimiento')
            df_agency_sla = df_agency_sla.sort_values('Tasa de Incumplimiento', ascending=False).head(10).sort_values('Tasa de Incumplimiento', ascending=True)

            idx_max_agency = df_agency_sla['Tasa de Incumplimiento'].idxmax()
            colores_agency = [COLOR_NEUTRO] * len(df_agency_sla)
            colores_agency[idx_max_agency] = COLOR_FOCO # Resaltar con COLOR_FOCO

            fig_agency_sla = px.bar(df_agency_sla, x='Tasa de Incumplimiento', y=agency_col, orientation='h')
            fig_agency_sla.update_traces(marker_color=colores_agency, opacity=0.85)
            fig_agency_sla.update_layout(
                showlegend=False, plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(**EJE_BASE_DICT, showgrid=False, tickformat=".0%", title_text="Tasa de Incumplimiento"),
                yaxis=dict(**EJE_BASE_DICT, title_text="Agencia"), height=400
            )
            st.plotly_chart(fig_agency_sla, use_container_width=True)

        with col_channel_sla:
            st.markdown("##### Tasa de Incumplimiento por Canal de Reporte")
            df_channel_sla = df_work.groupby(channel_col)[is_sla_non_compliant_col].mean().reset_index(name='Tasa de Incumplimiento')
            df_channel_sla = df_channel_sla.sort_values('Tasa de Incumplimiento', ascending=False)
            
            idx_max_channel = df_channel_sla['Tasa de Incumplimiento'].idxmax()
            colores_channel = [COLOR_NEUTRO] * len(df_channel_sla)
            colores_channel[idx_max_channel] = COLOR_FOCO # Resaltar con COLOR_FOCO

            fig_channel_sla = px.bar(df_channel_sla, x='Tasa de Incumplimiento', y=channel_col, orientation='h')
            fig_channel_sla.update_traces(marker_color=colores_channel, opacity=0.85)
            fig_channel_sla.update_layout(
                showlegend=False, plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(**EJE_BASE_DICT, showgrid=False, tickformat=".0%", title_text="Tasa de Incumplimiento"),
                yaxis=dict(**EJE_BASE_DICT, title_text="Canal de Reporte"), height=400
            )
            st.plotly_chart(fig_channel_sla, use_container_width=True)

    st.markdown("---")

    # ======================================================================
    # RANKING POR DISTRITO (Incumplimiento SLA)
    # ======================================================================
    if community_board_col and complaint_col:
        st.header("🏆 Ranking de Distritos por Riesgo de Incumplimiento de SLA")
        st.write("Identifica los distritos con la mayor tasa de incumplimiento y el tipo de queja más frecuente asociado a ese riesgo.")

        # Obtener la tasa de incumplimiento por distrito y la queja más común
        df_district_sla_agg = (
            df_cd_map_source.groupby(['borocd', 'boro_code', complaint_col])
            .agg(
                tasa_incumplimiento=(is_sla_non_compliant_col, 'mean'),
                conteo_quejas=('Unique Key', 'count')
            )
            .reset_index()
        )
        
        # Encontrar la queja más frecuente por distrito (basado en volumen, no en SLA)
        idx_top_complaint = df_district_sla_agg.loc[df_district_sla_agg.groupby('borocd')['conteo_quejas'].idxmax()]
        df_top_complaint_per_district = idx_top_complaint[['borocd', complaint_col]] \
                                        .rename(columns={complaint_col: 'Queja Más Frecuente (Volumen)'})

        df_district_full = df_sla_cd_rate.merge(df_top_complaint_per_district, on='borocd', how='left')
        df_district_full['Borough'] = df_district_full['boro_code'].map(BORO_NAMES)
        df_district_full['Distrito'] = df_district_full['borocd'].astype(str)
        df_district_full = df_district_full.rename(columns={'tasa_incumplimiento': 'Tasa Incumplimiento SLA'})
        
        tab_labels = ["🌆 Todos"] + [f"{BORO_NAMES[k]}" for k in sorted(BORO_NAMES.keys())]
        tabs = st.tabs(tab_labels)

        BORO_ACCENT = {1: "#FFCA28", 2: "#00E676", 3: "#1E88E5", 4: "#E91E63", 5: "#AB47BC"} # Colores para el ranking por borough

        def styled_ranking(df_in, accent_color="#D9383A"):
            df_show = (
                df_in[['Distrito', 'Borough', 'Tasa Incumplimiento SLA', 'Queja Más Frecuente (Volumen)']]
                .sort_values('Tasa Incumplimiento SLA', ascending=False)
                .reset_index(drop=True)
            )
            df_show.index += 1
            df_show['Tasa Incumplimiento SLA'] = df_show['Tasa Incumplimiento SLA'].apply(lambda x: f"{x:.1%}")
            return df_show

        with tabs[0]:
            df_all = styled_ranking(df_district_full)
            st.dataframe(df_all, use_container_width=True, height=400)

        for i, (boro_code, boro_name) in enumerate(sorted(BORO_NAMES.items()), start=1):
            with tabs[i]:
                df_b = df_district_full[df_district_full['boro_code'] == boro_code]
                if df_b.empty:
                    st.info(f"Sin datos para {boro_name}.")
                    continue
                df_show = styled_ranking(df_b, accent_color=BORO_ACCENT.get(boro_code, "#fff"))

                top_district = df_show.iloc[0]
                accent = BORO_ACCENT.get(boro_code, "#fff")
                st.markdown(
                    f"""<div style="padding:10px 14px;border-left:4px solid {accent};
                        background:rgba(0,0,0,0.04);border-radius:4px;margin-bottom:12px;">
                        <span style="color:{accent};font-size:12px;font-weight:700;">DISTRITO CON MAYOR INCUMPLIMIENTO DE SLA</span><br>
                        <span style="font-size:22px;font-weight:800;color:#1A202C;">Distrito {top_district['Distrito']}</span>
                        <span style="color:#4A5568;font-size:13px;margin-left:10px;">{top_district['Tasa Incumplimiento SLA']} de incumplimiento</span><br>
                        <span style="color:#4A5568;font-size:13px;">Queja dominante: <b style="color:#1A202C;">{top_district['Queja Más Frecuente (Volumen)']}</b></span>
                    </div>""",
                    unsafe_allow_html=True
                )
                st.dataframe(
                    df_show[['Distrito', 'Tasa Incumplimiento SLA', 'Queja Más Frecuente (Volumen)']],
                    use_container_width=True
                )
        st.caption(f"Los rankings muestran la tasa de incumplimiento de SLA por Community District. Las zonas con mayor tasa indican puntos críticos para la gestión operativa.")

    st.markdown("---")

    # ======================================================================
    # ANÁLISIS DE TIEMPOS DE RESOLUCIÓN GENERALES (Contexto)
    # Se utiliza df_raw aquí para mostrar el contexto general de todos los incidentes
    # ======================================================================
    if resolution_time_col:
        st.header("⚙️ Análisis de Tiempos de Resolución Generales (Contexto)")
        st.write("Estadísticas del tiempo que toma cerrar los incidentes, sin filtrar por SLA. Esto proporciona un contexto del rendimiento general.")

        df_res_general = df_raw[df_raw[resolution_time_col].notna()].copy()
        # Filtramos valores extremos para un histograma legible, ej. > 1 año
        df_res_general = df_res_general[(df_res_general[resolution_time_col] > 0) & (df_res_general[resolution_time_col] < 365)]

        if df_res_general.empty:
            st.info("No hay suficientes datos con tiempos de resolución válidos para un análisis general.")
        else:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("⏱ Tiempo Mediano", f"{df_res_general[resolution_time_col].median():.1f} días")
            k2.metric("⚡ Resolución Más Rápida", f"{df_res_general[resolution_time_col].min():.1f} días")
            k3.metric("🐢 Resolución Más Lenta", f"{df_res_general[resolution_time_col].max():.0f} días")
            k4.metric("📊 Promedio General", f"{df_res_general[resolution_time_col].mean():.1f} días")

            st.markdown("---")

            st.subheader("📊 Distribución del Tiempo de Resolución General")
            df_hist = df_res_general[df_res_general[resolution_time_col] <= 60] # Zoom en los primeros 60 días
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=df_hist[resolution_time_col],
                nbinsx=60,
                marker_color=COLOR_NEUTRO,
                opacity=0.85,
                name="Distribución"
            ))
            # Línea de mediana
            mediana = df_res_general[resolution_time_col].median()
            fig_hist.add_vline(
                x=mediana, line_dash="dash", line_color=COLOR_FOCO, line_width=2,
                annotation_text=f"Mediana: {mediana:.1f}d",
                annotation_font_color=COLOR_FOCO,
                annotation_position="top right"
            )
            fig_hist.update_layout(
                plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(**EJE_BASE_DICT, showgrid=False, title_text="Días hasta Resolución"),
                yaxis=dict(**EJE_BASE_DICT, showgrid=True, gridcolor="rgba(0,0,0,0.08)", title_text="Cantidad de Incidentes"),
                showlegend=False, height=350
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            st.caption("Vista limitada a los primeros 60 días para mejor lectura. La línea roja marca la mediana.")

