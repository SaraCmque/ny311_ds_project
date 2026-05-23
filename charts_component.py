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
        # Paleta de colores por borough (igual que el mapa de referencia)
        BORO_PALETTE = {1: "#E8A838", 2: "#6BAF92", 3: "#8B9DC3", 4: "#C4A882", 5: "#9B7BB5"}
        BORO_NAMES   = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}

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
            # Asignar color por borough y opacidad/z por incidentes
            max_inc = df_freq_cd['incidentes'].max()

            # Construir figura con un trace coroplético POR BOROUGH para colores distintos
            fig_cd = go.Figure()

            for boro_code, boro_name in BORO_NAMES.items():
                df_b = df_freq_cd[df_freq_cd['boro_code'] == boro_code]
                if df_b.empty:
                    continue

                base_color = BORO_PALETTE[boro_code]

                # Escala de color: blanco (baja carga) → color del borough (alta carga)
                colorscale_b = [
                    [0.0, "rgba(20,25,35,0.3)"],
                    [1.0, base_color]
                ]

                fig_cd.add_trace(go.Choroplethmapbox(
                    geojson=geojson_cd,
                    locations=df_b['borocd'],
                    z=df_b['incidentes'],
                    featureidkey="properties.BoroCD",
                    colorscale=colorscale_b,
                    zmin=0,
                    zmax=max_inc,
                    showscale=False,
                    marker_opacity=0.80,
                    marker_line_width=1.0,
                    marker_line_color="rgba(255,255,255,0.35)",
                    hovertemplate=(
                        f"<b>{boro_name}</b> — Distrito %{{location}}<br>"
                        "Incidentes: %{z:,}<extra></extra>"
                    ),
                    name=boro_name
                ))

            # Puntos superpuestos (muestra) coloreados por borough
            if lat_col and lon_col:
                df_pts = df_cd.dropna(subset=[lat_col, lon_col]).sample(n=min(5000, len(df_cd)))
                colores_pts = [BORO_PALETTE.get(int(b), "#718096") for b in df_pts['boro_code']]

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

            # Tabla resumen por borough
            df_summary = (
                df_freq_cd.groupby('boro_code')['incidentes']
                .sum()
                .reset_index()
            )
            df_summary['Borough'] = df_summary['boro_code'].map(BORO_NAMES)
            df_summary = df_summary.rename(columns={'incidentes': 'Total Incidentes'})\
                                   .sort_values('Total Incidentes', ascending=False)\
                                   .reset_index(drop=True)[['Borough', 'Total Incidentes']]
            df_summary.index += 1

            col_tbl, col_leg = st.columns([0.35, 0.65])
            with col_tbl:
                st.markdown("**Ranking por Borough**")
                st.dataframe(df_summary, use_container_width=True)
            with col_leg:
                leyenda_html = "".join([
                    f'<span style="display:inline-block;width:12px;height:12px;'
                    f'background:{BORO_PALETTE[k]};border-radius:2px;margin-right:6px;"></span>'
                    f'<span style="color:#E2E8F0;font-size:13px;">{v}</span>&nbsp;&nbsp;&nbsp;'
                    for k, v in BORO_NAMES.items()
                ])
                st.markdown(
                    f"""
                    <div style="padding:14px; border-left:4px solid #4A5568;
                                background:rgba(74,85,104,0.08); border-radius:4px; margin-top:6px;">
                        <div style="margin-bottom:10px;">{leyenda_html}</div>
                        <span style="color:#A0AEC0; font-size:13px;">
                            • El <b style="color:white;">tono más intenso</b> dentro de cada borough indica mayor carga de incidentes.<br>
                            • Los <b style="color:white;">puntos</b> representan incidentes individuales, coloreados por borough.<br>
                            • Hover sobre cada distrito para ver el conteo exacto.
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.caption(f"71 Community Districts · Columna detectada: '{community_col}' · Muestra de 5,000 puntos")