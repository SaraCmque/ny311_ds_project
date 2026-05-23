import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_dynamic_charts(df: pd.DataFrame):
    """Renderiza gráficas dinámicas optimizadas para la Ingeniería de la Atención."""
    
    st.header("Análisis Visual de Reportes (NYC 311)")
    
    if df is None or df.empty:
        st.warning("No hay datos disponibles.")
        return
    
    df_work = df.copy()
    
    # Mapeo estricto de columnas sobre las 210k filas de la capa Silver
    date_col = next((col for col in df_work.columns if 'created' in col.lower() and 'date' in col.lower()), None)
    closed_col = next((col for col in df_work.columns if 'closed' in col.lower() and 'date' in col.lower()), None)
    complaint_col = next((col for col in df_work.columns if 'complaint' in col.lower() and 'type' in col.lower()), None)
    borough_col = next((col for col in df_work.columns if 'borough' in col.lower()), None)
    
    # Normalización de marcas de tiempo
    if date_col:
        df_work[date_col] = pd.to_datetime(df_work[date_col], errors='coerce')
    if closed_col:
        df_work[closed_col] = pd.to_datetime(df_work[closed_col], errors='coerce')
    
    col_a, col_b = st.columns(2)

    # PALETA DE COLORES SELECTIVA (Gris para control, Rojo para llamar la atención)
    COLOR_FOCO = "#D9383A"       # Rojo estratégico
    COLOR_NEUTRO = "#4A5568"     # Gris oscuro sutil para barras secundarias
    COLOR_FONDO_LIGERO = "rgba(0,0,0,0)"
    
    # Configuración base reutilizable para dar contexto y enmarcar los ejes
    EJE_X_BASE = dict(
        showline=True,
        linewidth=1.2,
        linecolor="rgba(160, 174, 192, 0.4)",
        ticks="outside",
        tickfont=dict(color="#A0AEC0", size=10)
    )
    EJE_Y_BASE = dict(
        showline=True,
        linewidth=1.2,
        linecolor="rgba(160, 174, 192, 0.4)",
        ticks="outside",
        tickfont=dict(color="#A0AEC0", size=10)
    )

    with col_a:
        st.subheader("Top 10 Quejas Principalmente Críticas")
        if complaint_col:
            top_complaints = df_work[complaint_col].value_counts().head(10).reset_index()
            top_complaints.columns = ['Tipo', 'Cantidad']
            
            colores_quejas = [COLOR_NEUTRO] * len(top_complaints)
            colores_quejas[-1] = COLOR_FOCO  # La barra con más valor
            
            fig = px.bar(top_complaints, x='Cantidad', y='Tipo', orientation='h')
            fig.update_traces(marker_color=colores_quejas, marker_line_color=colores_quejas, opacity=0.85)
            
            fig.update_layout(
                showlegend=False,
                plot_bgcolor=COLOR_FONDO_LIGERO,
                paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(
                    **EJE_X_BASE,
                    showgrid=False,
                    title=dict(text="Número de Reportes", font=dict(color="#A0AEC0", size=11))
                ),
                yaxis=dict(
                    **EJE_Y_BASE,
                    categoryorder='total ascending',
                    title=dict(text="Tipo de Incidente", font=dict(color="#A0AEC0", size=11))
                )
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Distribución por Distrito (Volumen de Carga)")
        if borough_col:
            borough_dist = df_work[borough_col].value_counts().reset_index()
            borough_dist.columns = ['Distrito', 'Total']
            
            borough_dist = borough_dist.sort_values(by='Total', ascending=True)
            colores_distritos = [
                COLOR_FOCO if dist == "BROOKLYN" else COLOR_NEUTRO 
                for dist in borough_dist['Distrito']
            ]
            
            fig = px.bar(borough_dist, x='Total', y='Distrito', orientation='h')
            fig.update_traces(marker_color=colores_distritos, opacity=0.85)
            
            fig.update_layout(
                showlegend=False,
                plot_bgcolor=COLOR_FONDO_LIGERO,
                paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(
                    **EJE_X_BASE,
                    showgrid=False,
                    title=dict(text="Total de Reportes", font=dict(color="#A0AEC0", size=11))
                ),
                yaxis=dict(
                    **EJE_Y_BASE,
                    title=dict(text="Distrito (Borough)", font=dict(color="#A0AEC0", size=11))
                )
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    if date_col:
        st.subheader("Evolución Temporal de Incidentes")
        df_daily = df_work.groupby(df_work[date_col].dt.date).size().reset_index()
        df_daily.columns = ['Fecha', 'Total']
        
        idx_max = df_daily['Total'].idxmax()
        idx_min = df_daily['Total'].idxmin()
        row_max = df_daily.loc[idx_max]
        row_min = df_daily.loc[idx_min]

        fig = px.line(df_daily, x='Fecha', y='Total')
        fig.update_traces(line_color=COLOR_NEUTRO, line_width=2, name="Tendencia")
        
        # Pico Máximo (Rojo Estratégico)
        fig.add_trace(go.Scatter(
            x=[row_max['Fecha']], 
            y=[row_max['Total']],
            mode='markers+text',
            marker=dict(color=COLOR_FOCO, size=12, line=dict(width=2, color='white')),
            text=[f"Pico Máximo: {row_max['Total']}"],
            textposition="top center",
            textfont=dict(color="white", size=12),
            name="Máximo Histórico"
        ))
        
        # Punto Mínimo
        fig.add_trace(go.Scatter(
            x=[row_min['Fecha']], 
            y=[row_min['Total']],
            mode='markers+text',
            marker=dict(color="#63B3ED", size=10, line=dict(width=2, color='white')),
            text=[f"Mínimo: {row_min['Total']}"],
            textposition="bottom center",
            textfont=dict(color="#A0AEC0", size=11),
            name="Mínimo Histórico"
        ))
        
        fig.update_layout(
            showlegend=False,
            plot_bgcolor=COLOR_FONDO_LIGERO,
            paper_bgcolor=COLOR_FONDO_LIGERO,
            xaxis=dict(
                **EJE_X_BASE,
                showgrid=False,
                title=dict(text="Línea de Tiempo", font=dict(color="#A0AEC0", size=11))
            ),
            yaxis=dict(
                **EJE_Y_BASE,
                showgrid=True,
                gridcolor="rgba(200,200,200,0.08)",
                title=dict(text="Frecuencia Diaria de Casos", font=dict(color="#A0AEC0", size=11))
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        # ======================================================================
        # DISTRIBUCIÓN TEMPORAL: DÍA DE LA SEMANA Y DÍA DEL MES
        # ======================================================================
        df_work["weekday"] = df_work[date_col].dt.day_name().map({
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo"
        })
        df_work["day_of_month"] = df_work[date_col].dt.day

        weekday_dist = (
            df_work.groupby("weekday")
            .size()
            .reset_index(name="Total")
        )
        weekday_order = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        weekday_dist["weekday"] = pd.Categorical(weekday_dist["weekday"], categories=weekday_order, ordered=True)
        weekday_dist = weekday_dist.sort_values("weekday")

        day_of_month_dist = (
            df_work.groupby("day_of_month")
            .size()
            .reset_index(name="Total")
            .sort_values("day_of_month")
        )

        st.subheader("Patrones por Día de la Semana y Día del Mes")
        row_weekday, row_monthday = st.columns(2)

        with row_weekday:
            fig_weekday = px.bar(weekday_dist, x="Total", y="weekday", orientation="h")
            fig_weekday.update_traces(marker_color=COLOR_NEUTRO, opacity=0.85)
            fig_weekday.update_layout(
                showlegend=False,
                plot_bgcolor=COLOR_FONDO_LIGERO,
                paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis={
                    **EJE_X_BASE,
                    "showgrid": False,
                    "title": {"text": "Total de Reportes", "font": {"color": "#A0AEC0", "size": 11}}
                },
                yaxis={
                    **EJE_Y_BASE,
                    "title": {"text": "Día de la Semana", "font": {"color": "#A0AEC0", "size": 11}}
                }
            )
            st.plotly_chart(fig_weekday, use_container_width=True)

        with row_monthday:
            fig_day = px.bar(day_of_month_dist, x="day_of_month", y="Total")
            fig_day.update_traces(marker_color=COLOR_NEUTRO, opacity=0.85)
            fig_day.update_layout(
                showlegend=False,
                plot_bgcolor=COLOR_FONDO_LIGERO,
                paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis={
                    **EJE_X_BASE,
                    "title": {"text": "Día del Mes", "font": {"color": "#A0AEC0", "size": 11}}
                },
                yaxis={
                    **EJE_Y_BASE,
                    "title": {"text": "Total de Reportes", "font": {"color": "#A0AEC0", "size": 11}}
                }
            )
            st.plotly_chart(fig_day, use_container_width=True)

    st.divider()

    # ======================================================================
    # NUEVA SECCIÓN: EFICIENCIA OPERATIVA (DETECCIÓN DE ANOMALÍAS EN SLAs)
    # ======================================================================
    st.subheader("⏳ Eficiencia y Cuellos de Botella en Respuesta (SLAs)")
    st.write("Análisis del tiempo promedio requerido para resolver y cerrar incidentes por categoría.")
    
    if date_col and closed_col and complaint_col:
        df_work['dias_resolucion'] = (df_work[closed_col] - df_work[date_col]).dt.total_seconds() / 86400
        df_sla = df_work[df_work['dias_resolucion'] >= 0].dropna(subset=['dias_resolucion'])
        
        if not df_sla.empty:
            df_sla_avg = df_sla.groupby(complaint_col)['dias_resolucion'].mean().reset_index()
            df_sla_avg = df_sla_avg.sort_values(by='dias_resolucion', ascending=False).head(10)
            df_sla_avg = df_sla_avg.sort_values(by='dias_resolucion', ascending=True)
            
            colores_sla = [COLOR_NEUTRO] * len(df_sla_avg)
            colores_sla[-1] = COLOR_FOCO  
            
            fig_sla = px.bar(df_sla_avg, x='dias_resolucion', y=complaint_col, orientation='h')
            fig_sla.update_traces(marker_color=colores_sla, opacity=0.9)
            
            peor_cat = df_sla_avg.iloc[-1][complaint_col]
            peor_dia = df_sla_avg.iloc[-1]['dias_resolucion']
            
            fig_sla.update_layout(
                plot_bgcolor=COLOR_FONDO_LIGERO,
                paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(
                    **EJE_X_BASE,
                    showgrid=True,
                    gridcolor="rgba(100,100,100,0.1)",
                    title=dict(text="Días Promedio de Cierre", font=dict(color="#A0AEC0", size=11))
                ),
                yaxis=dict(
                    **EJE_Y_BASE,
                    title=dict(text="Categoría de Incidente", font=dict(color="#A0AEC0", size=11))
                ),
                xaxis_range=[0, peor_dia * 1.3],
                annotations=[
                    dict(
                        x=peor_dia,
                        y=peor_cat,
                        text=f"⚠️ <b>RETRASO ANORMAL DETECTADO</b><br>La categoría <i>{peor_cat}</i> de la ciudad<br>rompe los SLAs con {peor_dia:.1f} días promedio.",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor=COLOR_FOCO,
                        ax=80,
                        ay=0,
                        font=dict(color=COLOR_FOCO, size=11),
                        bgcolor="rgba(255, 255, 255, 0.95)",
                        bordercolor=COLOR_FOCO,
                        borderwidth=1
                    )
                ]
            )
            st.plotly_chart(fig_sla, use_container_width=True)
        else:
            st.info("No hay suficientes registros con fechas de cierre válidas para procesar SLAs.")
            
    st.divider()

    # ======================================================================
    # CONTINUIDAD: CONCENTRACIÓN GEOGRÁFICA ORIGINAL
    # ======================================================================
    lat_col = next((col for col in df_work.columns if col.lower() == 'latitude'), None)
    lon_col = next((col for col in df_work.columns if col.lower() == 'longitude'), None)
    
    if lat_col and lon_col:
        st.subheader("Concentración Geográfica de Incidentes")
        df_map = df_work.dropna(subset=[lat_col, lon_col]).sample(n=min(5000, len(df_work)))
        
        fig = px.scatter_mapbox(df_map, lat=lat_col, lon=lon_col,
                                hover_name=complaint_col if complaint_col else None,
                                zoom=10, height=600, mapbox_style="carto-darkmatter")
        
        if borough_col:
            colores_mapa = [COLOR_FOCO if b == "BROOKLYN" else "#718096" for b in df_map[borough_col]]
            fig.update_traces(marker=dict(color=colores_mapa, size=4, opacity=0.6))
            
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Nota: Muestra aleatoria de 5,000 registros para optimización de memoria.")

    st.divider()

    # ======================================================================
    # MAPA: COMMUNITY DISTRICTS DE NYC CON DENSIDAD DE INCIDENTES
    # ======================================================================
    st.subheader("🗺️ Incidentes por Community District (NYC)")
    st.write("Cada polígono representa un Community District. El tono de color indica el volumen de reportes.")

    # Columna Community Board del dataset NYC 311 (formato: "01 BROOKLYN", "12 QUEENS", etc.)
    community_col = next(
        (col for col in df_work.columns if 'community' in col.lower() and 'board' in col.lower()),
        next((col for col in df_work.columns if 'community' in col.lower()), None)
    )

    if not lat_col or not lon_col:
        st.info("No hay columnas de latitud/longitud disponibles para este mapa.")
    elif not community_col:
        st.info(f"No se encontró la columna 'Community Board' en el dataset. Columnas disponibles: {list(df_work.columns)}")
    else:
        import requests

        # Mapa borough name → código numérico para construir BoroCD
        BORO_CODE = {
            "MANHATTAN": 1, "MN": 1,
            "BRONX": 2,     "BX": 2,
            "BROOKLYN": 3,  "BK": 3,
            "QUEENS": 4,    "QN": 4, "QS": 4,
            "STATEN ISLAND": 5, "SI": 5,
        }
        # Paleta de colores por borough — cada uno con escala propia de baja a alta intensidad
        BORO_NAMES = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}

        # Escala por borough: [0=vacío, 0.2=pálido, 1.0=color vivo máximo]
        BORO_SCALES = {
            1: [[0.0, "rgba(20,25,35,0.15)"], [0.2, "#FFF59D"], [0.55, "#FFCA28"], [1.0, "#FF6F00"]],   # Manhattan: amarillo → naranja intenso
            2: [[0.0, "rgba(20,25,35,0.15)"], [0.2, "#B9F6CA"], [0.55, "#00E676"], [1.0, "#00695C"]],   # Bronx: verde menta → verde profundo
            3: [[0.0, "rgba(20,25,35,0.15)"], [0.2, "#BBDEFB"], [0.55, "#1E88E5"], [1.0, "#0D47A1"]],   # Brooklyn: celeste → azul marino
            4: [[0.0, "rgba(20,25,35,0.15)"], [0.2, "#F8BBD9"], [0.55, "#E91E63"], [1.0, "#880E4F"]],   # Queens: rosa → fucsia profundo
            5: [[0.0, "rgba(20,25,35,0.15)"], [0.2, "#E1BEE7"], [0.55, "#AB47BC"], [1.0, "#4A148C"]],   # Staten Island: lila → morado oscuro
        }
        # Color representativo de cada borough (tono medio) para puntos y leyenda
        BORO_COLOR = {1: "#FFCA28", 2: "#00E676", 3: "#1E88E5", 4: "#E91E63", 5: "#AB47BC"}

        def parse_borocd(val):
            """Convierte '01 BROOKLYN' → 301, '12 QUEENS' → 412, etc."""
            try:
                parts = str(val).strip().split()
                if len(parts) < 2:
                    return None
                num = int(parts[0])
                boro_str = " ".join(parts[1:]).upper()
                # Busca coincidencia exacta o parcial
                code = BORO_CODE.get(boro_str)
                if code is None:
                    for key, v in BORO_CODE.items():
                        if key in boro_str or boro_str in key:
                            code = v
                            break
                if code is None:
                    return None
                return code * 100 + num
            except Exception:
                return None

        df_cd = df_work.dropna(subset=[community_col]).copy()
        df_cd['borocd'] = df_cd[community_col].apply(parse_borocd)
        df_cd = df_cd.dropna(subset=['borocd'])
        df_cd['borocd'] = df_cd['borocd'].astype(int)
        df_cd['boro_code'] = (df_cd['borocd'] // 100).astype(int)

        # Frecuencia por Community District
        df_freq_cd = df_cd.groupby(['borocd', 'boro_code']).size().reset_index(name='incidentes')

        # Descarga del GeoJSON
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
            st.caption("⚠️ GeoJSON no disponible. Mostrando mapa de puntos por Community District.")
            fig_cd_fall = px.scatter_mapbox(
                df_cd.dropna(subset=[lat_col, lon_col]).sample(n=min(8000, len(df_cd))),
                lat=lat_col, lon=lon_col,
                color='boro_code',
                color_continuous_scale=list(BORO_PALETTE.values()),
                zoom=10, height=640, mapbox_style="carto-darkmatter"
            )
            fig_cd_fall.update_layout(margin=dict(t=10,b=10,l=10,r=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_cd_fall, use_container_width=True)
        else:
            # ── Control de filtro de criticidad ────────────────────────────
            col_toggle, col_desc = st.columns([0.35, 0.65])
            with col_toggle:
                solo_criticos = st.toggle(
                    "🔴 Solo zonas críticas",
                    value=False,
                    help="Activa para ocultar distritos de baja carga y resaltar solo los más saturados."
                )
            with col_desc:
                if solo_criticos:
                    st.markdown(
                        "<div style='padding:8px 12px;background:rgba(217,56,58,0.12);"
                        "border-left:3px solid #FF0055;border-radius:4px;margin-top:4px;'>"
                        "<span style='color:#FF0055;font-size:12px;font-weight:700;'>MODO CRÍTICO ACTIVO</span>"
                        "<span style='color:#A0AEC0;font-size:12px;'> · Solo se muestran los distritos en el top 30% de incidentes por borough.</span>"
                        "</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        "<div style='padding:8px 12px;background:rgba(74,85,104,0.12);"
                        "border-left:3px solid #4A5568;border-radius:4px;margin-top:4px;'>"
                        "<span style='color:#A0AEC0;font-size:12px;'>Todos los distritos visibles · "
                        "Activa el botón para resaltar solo las zonas más críticas.</span>"
                        "</div>",
                        unsafe_allow_html=True
                    )

            # Asignar color por borough y opacidad/z por incidentes
            max_inc = df_freq_cd['incidentes'].max()

            # Construir figura con un trace coroplético POR BOROUGH para colores distintos
            fig_cd = go.Figure()

            for boro_code, boro_name in BORO_NAMES.items():
                df_b = df_freq_cd[df_freq_cd['boro_code'] == boro_code].copy()
                if df_b.empty:
                    continue

                boro_max = df_b['incidentes'].max() if not df_b.empty else 1

                if solo_criticos:
                    # Umbral: percentil 70 dentro del borough → solo muestra el top 30%
                    umbral = df_b['incidentes'].quantile(0.70)
                    df_b = df_b[df_b['incidentes'] >= umbral]
                    if df_b.empty:
                        continue
                fig_cd.add_trace(go.Choroplethmapbox(
                    geojson=geojson_cd,
                    locations=df_b['borocd'],
                    z=df_b['incidentes'],
                    featureidkey="properties.BoroCD",
                    colorscale=BORO_SCALES[boro_code],
                    zmin=0,
                    zmax=boro_max,          # escala independiente por borough
                    showscale=False,
                    marker_opacity=0.88,
                    marker_line_width=1.4,
                    marker_line_color="rgba(255,255,255,0.45)",
                    hovertemplate=(
                        f"<b>{boro_name}</b> — Distrito %{{location}}<br>"
                        "Incidentes: <b>%{z:,}</b><extra></extra>"
                    ),
                    name=boro_name
                ))

            # Puntos superpuestos (muestra) coloreados por borough
            if lat_col and lon_col:
                df_pts_src = df_cd.dropna(subset=[lat_col, lon_col])
                if solo_criticos:
                    # Solo puntos de distritos críticos (top 30% global)
                    umbral_global = df_freq_cd['incidentes'].quantile(0.70)
                    distritos_criticos = set(
                        df_freq_cd[df_freq_cd['incidentes'] >= umbral_global]['borocd'].astype(int).tolist()
                    )
                    df_pts_src = df_pts_src[df_pts_src['borocd'].astype(int).isin(distritos_criticos)]
                df_pts = df_pts_src.sample(n=min(5000, len(df_pts_src))) if not df_pts_src.empty else df_pts_src
                colores_pts = [BORO_COLOR.get(int(b) // 100, "#718096") for b in df_pts['borocd']]

                fig_cd.add_trace(go.Scattermapbox(
                    lat=df_pts[lat_col],
                    lon=df_pts[lon_col],
                    mode='markers',
                    marker=dict(size=3, color=colores_pts, opacity=0.45),
                    hovertemplate=(
                        "Distrito: %{customdata}<br>"
                        + (f"Queja: %{{text}}<br>" if complaint_col else "")
                        + "<extra></extra>"
                    ),
                    text=df_pts[complaint_col].astype(str) if complaint_col else None,
                    customdata=df_pts['borocd'],
                    name="Puntos"
                ))

            fig_cd.update_layout(
                mapbox=dict(
                    style="carto-darkmatter",
                    center=dict(lat=40.7128, lon=-74.0060),
                    zoom=10
                ),
                margin=dict(t=10, b=10, l=10, r=10),
                height=660,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom", y=0.01,
                    xanchor="left", x=0.01,
                    bgcolor="rgba(15,20,30,0.75)",
                    font=dict(color="#E2E8F0", size=11),
                    itemclick=False
                ),
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_cd, use_container_width=True)

            # ── Leyenda de colores ──────────────────────────────────────────
            leyenda_items = "".join([
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
                f'<div style="width:48px;height:14px;border-radius:3px;'
                f'background:linear-gradient(to right,{BORO_SCALES[k][1][1]},{BORO_SCALES[k][-1][1]});"></div>'
                f'<span style="color:#E2E8F0;font-size:13px;"><b>{v}</b> — pálido = poco · saturado = mucho</span></div>'
                for k, v in BORO_NAMES.items()
            ])
            st.markdown(
                f"""
                <div style="padding:12px 16px; border-left:4px solid #4A5568;
                            background:rgba(74,85,104,0.08); border-radius:4px; margin-bottom:18px;">
                    <span style="color:#E2E8F0; font-size:12px; font-weight:700; letter-spacing:1px;">LEYENDA DE COLORES</span><br><br>
                    {leyenda_items}
                </div>
                """,
                unsafe_allow_html=True
            )

            # ── Ranking por distrito dentro de cada Borough ─────────────────
            st.markdown("### 🏆 Ranking de Distritos por Borough")

            # Tarjeta FOCO CRÍTICO OPERATIVO: queja más repetida en todo el dataset
            if complaint_col:
                queja_global = df_cd[complaint_col].value_counts()
                complaint_moda   = queja_global.index[0] if not queja_global.empty else "N/A"
                # Descriptor más común asociado a esa queja
                descriptor_col = next((c for c in df_cd.columns if 'descriptor' in c.lower()), None)
                if descriptor_col:
                    descriptor_moda = (
                        df_cd[df_cd[complaint_col] == complaint_moda][descriptor_col]
                        .value_counts().index[0]
                        if not df_cd[df_cd[complaint_col] == complaint_moda].empty else "N/A"
                    )
                else:
                    descriptor_moda = "N/A"

                st.markdown(
                    f"""
                    <div style="
                        background-color: rgba(217, 56, 58, 0.08);
                        border-left: 5px solid #FF0055;
                        padding: 20px;
                        border-radius: 6px;
                        margin-bottom: 22px;
                        border-top: 1px solid rgba(217, 56, 58, 0.2);
                        border-right: 1px solid rgba(217, 56, 58, 0.2);
                        border-bottom: 1px solid rgba(217, 56, 58, 0.2);
                    ">
                        <span style="color:#FF0055; font-size:13px; font-weight:bold; letter-spacing:1px;">🚨 FOCO CRÍTICO OPERATIVO</span>
                        <h2 style="margin: 5px 0 0 0; font-size: 30px; font-weight: 800; color: #FF0055;">{complaint_moda}</h2>
                        <p style="margin: 5px 0 0 0; font-size: 14px; color: #718096;">
                            Esta es la categoría con mayor recurrencia en toda la ciudad.
                            Específicamente bajo la modalidad de: <b>{descriptor_moda}</b>.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.write("Top distritos con más incidentes y el tipo de queja más frecuente en cada uno.")

            # Construir tabla enriquecida: borocd + incidentes + queja más común
            if complaint_col:
                df_district_detail = (
                    df_cd.groupby(['borocd', 'boro_code', complaint_col])
                    .size()
                    .reset_index(name='cnt')
                )
                # Queja más común por distrito
                idx_top = df_district_detail.groupby('borocd')['cnt'].idxmax()
                df_top_complaint = df_district_detail.loc[idx_top][['borocd', complaint_col]]\
                                                     .rename(columns={complaint_col: 'Queja Más Frecuente'})
                df_district_full = df_freq_cd.merge(df_top_complaint, on='borocd', how='left')
            else:
                df_district_full = df_freq_cd.copy()
                df_district_full['Queja Más Frecuente'] = 'N/A'

            df_district_full['Borough'] = df_district_full['boro_code'].map(BORO_NAMES)
            df_district_full['Distrito'] = df_district_full['borocd'].astype(str)
            df_district_full = df_district_full.rename(columns={'incidentes': 'Total Incidentes'})

            # Tabs: uno por borough + uno global
            tab_labels = ["🌆 Todos"] + [f"{BORO_NAMES[k]}" for k in sorted(BORO_NAMES.keys())]
            tabs = st.tabs(tab_labels)

            BORO_ACCENT = {1: "#FFCA28", 2: "#00E676", 3: "#1E88E5", 4: "#E91E63", 5: "#AB47BC"}

            def styled_ranking(df_in, accent="#D9383A"):
                df_show = (
                    df_in[['Distrito', 'Borough', 'Total Incidentes', 'Queja Más Frecuente']]
                    .sort_values('Total Incidentes', ascending=False)
                    .reset_index(drop=True)
                )
                df_show.index += 1
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
                    df_show = styled_ranking(df_b, accent=BORO_ACCENT.get(boro_code, "#fff"))

                    top_district = df_show.iloc[0]
                    accent = BORO_ACCENT.get(boro_code, "#fff")
                    st.markdown(
                        f"""<div style="padding:10px 14px;border-left:4px solid {accent};
                            background:rgba(0,0,0,0.15);border-radius:4px;margin-bottom:12px;">
                            <span style="color:{accent};font-size:12px;font-weight:700;">DISTRITO MÁS CRÍTICO</span><br>
                            <span style="font-size:22px;font-weight:800;color:white;">Distrito {top_district['Distrito']}</span>
                            <span style="color:#A0AEC0;font-size:13px;margin-left:10px;">{int(top_district['Total Incidentes']):,} incidentes</span><br>
                            <span style="color:#A0AEC0;font-size:13px;">Queja dominante: <b style="color:white;">{top_district['Queja Más Frecuente']}</b></span>
                        </div>""",
                        unsafe_allow_html=True
                    )
                    st.dataframe(
                        df_show[['Distrito', 'Total Incidentes', 'Queja Más Frecuente']],
                        use_container_width=True
                    )
            st.caption(f"71 Community Districts · Columna detectada: '{community_col}' · Muestra de 5,000 puntos")

    st.divider()

    # ======================================================================
    # SECCIÓN: ANÁLISIS DE RESOLUCIÓN DE INCIDENTES
    # ======================================================================
    resolution_date_col = next(
        (col for col in df_work.columns if 'resolution' in col.lower() and 'date' in col.lower()),
        next((col for col in df_work.columns if 'action' in col.lower() and 'date' in col.lower()), None)
    )
    resolution_desc_col = next(
        (col for col in df_work.columns if 'resolution' in col.lower() and 'description' in col.lower()), None
    )

    if resolution_date_col and date_col:
        st.header("⚙️ Análisis de Resolución de Incidentes")
        st.write("Tiempos de cierre y patrones de resolución extraídos del campo *Resolution Action Updated Date*.")

        df_res = df_work.copy()
        df_res[resolution_date_col] = pd.to_datetime(df_res[resolution_date_col], errors='coerce')
        df_res['horas_resolucion'] = (
            df_res[resolution_date_col] - df_res[date_col]
        ).dt.total_seconds() / 3600

        # Filtrar: solo tiempos positivos y razonables (< 1 año = 8760h)
        df_res = df_res[(df_res['horas_resolucion'] > 0) & (df_res['horas_resolucion'] < 8760)].copy()
        df_res['dias_resolucion'] = df_res['horas_resolucion'] / 24

        if df_res.empty:
            st.info("No hay suficientes datos con fechas de resolución válidas.")
        else:
            # ── KPIs globales ───────────────────────────────────────────────
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("⏱ Tiempo Mediano", f"{df_res['dias_resolucion'].median():.1f} días")
            k2.metric("⚡ Resolución Más Rápida", f"{df_res['horas_resolucion'].min():.1f} h")
            k3.metric("🐢 Resolución Más Lenta", f"{df_res['dias_resolucion'].max():.0f} días")
            k4.metric("📊 Promedio General", f"{df_res['dias_resolucion'].mean():.1f} días")

            st.divider()

            # ── Gráfica 1: Distribución de tiempos (histograma) ────────────
            st.subheader("📊 Distribución del Tiempo de Resolución")
            df_hist = df_res[df_res['dias_resolucion'] <= 60]  # zoom: primeros 60 días
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=df_hist['dias_resolucion'],
                nbinsx=60,
                marker_color=COLOR_NEUTRO,
                opacity=0.85,
                name="Distribución"
            ))
            # Línea de mediana
            mediana = df_res['dias_resolucion'].median()
            fig_hist.add_vline(
                x=mediana, line_dash="dash", line_color=COLOR_FOCO, line_width=2,
                annotation_text=f"Mediana: {mediana:.1f}d",
                annotation_font_color=COLOR_FOCO,
                annotation_position="top right"
            )
            fig_hist.update_layout(
                plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(**EJE_X_BASE, showgrid=False,
                           title=dict(text="Días hasta Resolución", font=dict(color="#A0AEC0", size=11))),
                yaxis=dict(**EJE_Y_BASE, showgrid=True, gridcolor="rgba(200,200,200,0.06)",
                           title=dict(text="Cantidad de Incidentes", font=dict(color="#A0AEC0", size=11))),
                showlegend=False, height=350
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            st.caption("Vista limitada a los primeros 60 días para mejor lectura. La línea roja marca la mediana.")

            st.divider()

            # ── Gráficas 2 y 3: Peores y mejores tiempos por tipo de queja ─
            if complaint_col:
                df_avg_tipo = (
                    df_res.groupby(complaint_col)['dias_resolucion']
                    .agg(['mean', 'median', 'count'])
                    .reset_index()
                    .rename(columns={'mean': 'promedio', 'median': 'mediana', 'count': 'casos'})
                )
                df_avg_tipo = df_avg_tipo[df_avg_tipo['casos'] >= 30]  # mínimo estadístico

                col_worst, col_best = st.columns(2)

                with col_worst:
                    st.subheader("🚨 Peores Tiempos por Tipo de Queja")
                    st.caption("Top 10 categorías con mayor demora promedio.")
                    df_worst = df_avg_tipo.nlargest(10, 'promedio').sort_values('promedio', ascending=True)
                    colores_w = [COLOR_NEUTRO] * len(df_worst)
                    colores_w[-1] = COLOR_FOCO
                    fig_worst = px.bar(df_worst, x='promedio', y=complaint_col, orientation='h')
                    fig_worst.update_traces(marker_color=colores_w, opacity=0.9,
                                            customdata=df_worst[['mediana', 'casos']],
                                            hovertemplate="<b>%{y}</b><br>Promedio: %{x:.1f}d<br>Mediana: %{customdata[0]:.1f}d<br>Casos: %{customdata[1]:,}<extra></extra>")
                    fig_worst.update_layout(
                        plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                        xaxis=dict(**EJE_X_BASE, showgrid=True, gridcolor="rgba(200,200,200,0.06)",
                                   title=dict(text="Días Promedio", font=dict(color="#A0AEC0", size=11))),
                        yaxis=dict(**EJE_Y_BASE, title=dict(text="", font=dict(color="#A0AEC0", size=11))),
                        showlegend=False, height=370
                    )
                    st.plotly_chart(fig_worst, use_container_width=True)

                with col_best:
                    st.subheader("✅ Mejores Tiempos por Tipo de Queja")
                    st.caption("Top 10 categorías resueltas más rápido en promedio.")
                    df_best = df_avg_tipo.nsmallest(10, 'promedio').sort_values('promedio', ascending=False)
                    colores_b = ["#00C853"] * len(df_best)
                    colores_b[0] = "#69F0AE"
                    fig_best = px.bar(df_best, x='promedio', y=complaint_col, orientation='h')
                    fig_best.update_traces(marker_color=colores_b, opacity=0.9,
                                           customdata=df_best[['mediana', 'casos']],
                                           hovertemplate="<b>%{y}</b><br>Promedio: %{x:.1f}d<br>Mediana: %{customdata[0]:.1f}d<br>Casos: %{customdata[1]:,}<extra></extra>")
                    fig_best.update_layout(
                        plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                        xaxis=dict(**EJE_X_BASE, showgrid=True, gridcolor="rgba(200,200,200,0.06)",
                                   title=dict(text="Días Promedio", font=dict(color="#A0AEC0", size=11))),
                        yaxis=dict(**EJE_Y_BASE, title=dict(text="", font=dict(color="#A0AEC0", size=11))),
                        showlegend=False, height=370
                    )
                    st.plotly_chart(fig_best, use_container_width=True)

            st.divider()

            # ── Gráfica 4: Evolución del tiempo de resolución en el tiempo ─
            st.subheader("📈 Evolución del Tiempo Promedio de Resolución")
            st.caption("¿Ha mejorado o empeorado la velocidad de respuesta a lo largo del período?")
            df_res['mes'] = df_res[date_col].dt.to_period('M').astype(str)
            df_evol = (
                df_res.groupby('mes')['dias_resolucion']
                .agg(['mean', 'median'])
                .reset_index()
                .rename(columns={'mean': 'Promedio', 'median': 'Mediana'})
                .sort_values('mes')
            )
            fig_evol = go.Figure()
            fig_evol.add_trace(go.Scatter(
                x=df_evol['mes'], y=df_evol['Promedio'],
                mode='lines+markers', name='Promedio',
                line=dict(color=COLOR_FOCO, width=2),
                marker=dict(size=6, color=COLOR_FOCO)
            ))
            fig_evol.add_trace(go.Scatter(
                x=df_evol['mes'], y=df_evol['Mediana'],
                mode='lines+markers', name='Mediana',
                line=dict(color="#63B3ED", width=2, dash='dot'),
                marker=dict(size=5, color="#63B3ED")
            ))
            fig_evol.update_layout(
                plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(**EJE_X_BASE, showgrid=False,
                           title=dict(text="Mes", font=dict(color="#A0AEC0", size=11)),
                           tickangle=-35),
                yaxis=dict(**EJE_Y_BASE, showgrid=True, gridcolor="rgba(200,200,200,0.06)",
                           title=dict(text="Días hasta Resolución", font=dict(color="#A0AEC0", size=11))),
                legend=dict(font=dict(color="#A0AEC0"), bgcolor="rgba(0,0,0,0)"),
                height=380
            )
            st.plotly_chart(fig_evol, use_container_width=True)

            st.divider()

            # ── Gráfica 5: Análisis por descripción de resolución ──────────
            if resolution_desc_col:
                st.subheader("📋 Descripción de Resolución vs Tiempo Promedio")
                st.caption("Qué acciones de resolución toman más tiempo en promedio.")
                df_desc_avg = (
                    df_res.groupby(resolution_desc_col)['dias_resolucion']
                    .agg(['mean', 'count'])
                    .reset_index()
                    .rename(columns={'mean': 'promedio', 'count': 'casos'})
                )
                df_desc_avg = df_desc_avg[df_desc_avg['casos'] >= 20]\
                    .nlargest(12, 'promedio')\
                    .sort_values('promedio', ascending=True)

                # Truncar textos largos
                df_desc_avg['desc_short'] = df_desc_avg[resolution_desc_col].str[:55] + "…"

                colores_desc = [COLOR_NEUTRO] * len(df_desc_avg)
                colores_desc[-1] = COLOR_FOCO

                fig_desc = px.bar(df_desc_avg, x='promedio', y='desc_short', orientation='h')
                fig_desc.update_traces(
                    marker_color=colores_desc, opacity=0.88,
                    customdata=df_desc_avg[[resolution_desc_col, 'casos']],
                    hovertemplate="<b>%{customdata[0]}</b><br>Promedio: %{x:.1f}d<br>Casos: %{customdata[1]:,}<extra></extra>"
                )
                fig_desc.update_layout(
                    plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                    xaxis=dict(**EJE_X_BASE, showgrid=True, gridcolor="rgba(200,200,200,0.06)",
                               title=dict(text="Días Promedio", font=dict(color="#A0AEC0", size=11))),
                    yaxis=dict(**EJE_Y_BASE, title=dict(text="", font=dict(color="#A0AEC0", size=11))),
                    showlegend=False,
                    height=max(350, len(df_desc_avg) * 32)
                )
                st.plotly_chart(fig_desc, use_container_width=True)

            # ── Gráfica 6: Box plot por borough ─────────────────────────────
            if borough_col:
                st.subheader("📦 Variabilidad del Tiempo de Resolución por Borough")
                st.caption("Distribución completa (mediana, percentiles y outliers) por zona.")
                df_box = df_res[df_res['dias_resolucion'] <= 90].dropna(subset=[borough_col])
                fig_box = go.Figure()
                borough_order = df_box.groupby(borough_col)['dias_resolucion'].median()\
                                      .sort_values(ascending=False).index.tolist()
                for boro in borough_order:
                    vals = df_box[df_box[borough_col] == boro]['dias_resolucion']
                    fig_box.add_trace(go.Box(
                        y=vals, name=boro,
                        marker_color=COLOR_FOCO if vals.median() == df_box.groupby(borough_col)['dias_resolucion'].median().max() else COLOR_NEUTRO,
                        line_color="#A0AEC0",
                        fillcolor="rgba(74,85,104,0.3)",
                        boxmean=True
                    ))
                fig_box.update_layout(
                    plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO,
                    xaxis=dict(**EJE_X_BASE, title=dict(text="Borough", font=dict(color="#A0AEC0", size=11))),
                    yaxis=dict(**EJE_Y_BASE, showgrid=True, gridcolor="rgba(200,200,200,0.06)",
                               title=dict(text="Días hasta Resolución", font=dict(color="#A0AEC0", size=11))),
                    showlegend=False, height=420
                )
                st.plotly_chart(fig_box, use_container_width=True)
                st.caption("Vista limitada a 90 días. La 'X' dentro de la caja indica el promedio.")