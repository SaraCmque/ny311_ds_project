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
    # MAPA: DENSIDAD POR CITY COUNCIL DISTRICTS + PUNTOS DE FRECUENCIA
    # ======================================================================

    # Detección robusta del nombre de columna (acepta espacios, guiones bajos, mayúsculas)
    council_col = next(
        (col for col in df_work.columns
         if 'council' in col.lower() and 'district' in col.lower()),
        None
    )

    st.subheader("🗳️ Densidad por City Council Districts")

    if not lat_col or not lon_col:
        st.info("No hay columnas de latitud/longitud disponibles para este mapa.")
    elif not council_col:
        st.info(f"No se encontró la columna 'City Council Districts' en el dataset. Columnas disponibles: {list(df_work.columns)}")
    else:
        import requests

        # --- Preparar datos del distrito ---
        df_council_valid = df_work.dropna(subset=[council_col, lat_col, lon_col]).copy()
        df_council_valid[council_col] = pd.to_numeric(df_council_valid[council_col], errors='coerce')
        df_council_valid = df_council_valid.dropna(subset=[council_col])
        df_council_valid[council_col] = df_council_valid[council_col].astype(int).astype(str)

        df_freq = df_council_valid[council_col].value_counts().reset_index()
        df_freq.columns = ['district', 'frecuencia']
        top3_districts = df_freq.nlargest(3, 'frecuencia')['district'].tolist()

        # --- Intento de descarga del GeoJSON con diagnóstico ---
        GEOJSON_URLS = [
            "https://data.cityofnewyork.us/api/geospatial/yusd-j4xi?method=export&type=GeoJSON",
            "https://raw.githubusercontent.com/ResidentMario/geoplot-data/master/nyc-council-districts.geojson",
        ]

        @st.cache_data(ttl=3600, show_spinner="Cargando geometrías de distritos...")
        def fetch_council_geojson_robust():
            for url in GEOJSON_URLS:
                try:
                    r = requests.get(url, timeout=20)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("features"):
                            return data, url
                except Exception:
                    continue
            return None, None

        geojson_data, geojson_source = fetch_council_geojson_robust()

        # Detectar la propiedad de ID correcta en el GeoJSON descargado
        featureid_key = "properties.CounDist"
        if geojson_data:
            sample_props = geojson_data["features"][0].get("properties", {}) if geojson_data["features"] else {}
            for candidate in ["CounDist", "coundist", "COUNDIST", "district", "DISTRICT", "id", "ID"]:
                if candidate in sample_props:
                    featureid_key = f"properties.{candidate}"
                    break
            # Asegurarse de que locations coincidan en tipo con el GeoJSON
            prop_val = sample_props.get(featureid_key.replace("properties.", ""), "")
            if isinstance(prop_val, int):
                df_freq['district_match'] = df_freq['district'].astype(int)
            else:
                df_freq['district_match'] = df_freq['district'].astype(str)

        # --- Construcción del mapa ---
        fig_council = go.Figure()

        if geojson_data:
            fig_council.add_trace(go.Choroplethmapbox(
                geojson=geojson_data,
                locations=df_freq['district_match'] if 'district_match' in df_freq.columns else df_freq['district'],
                z=df_freq['frecuencia'],
                featureidkey=featureid_key,
                colorscale=[
                    [0.0,  "rgba(30, 40, 60, 0.55)"],
                    [0.35, "rgba(100, 40, 50, 0.70)"],
                    [0.65, "rgba(180, 35, 35, 0.85)"],
                    [1.0,  "#D9383A"]
                ],
                marker_opacity=0.72,
                marker_line_width=1.2,
                marker_line_color="rgba(255,255,255,0.25)",
                colorbar=dict(
                    title=dict(text="Incidentes", font=dict(color="#A0AEC0", size=11)),
                    tickfont=dict(color="#A0AEC0"),
                    bgcolor="rgba(0,0,0,0)",
                    borderwidth=0,
                    thickness=14,
                    len=0.6
                ),
                hovertemplate="<b>Distrito %{location}</b><br>Incidentes: %{z:,}<extra></extra>",
                name="Densidad Distritos"
            ))
        else:
            # Fallback: mapa de calor por densidad de puntos usando density_mapbox
            st.caption("⚠️ Límites GeoJSON no disponibles. Mostrando mapa de calor de densidad.")
            fig_council = px.density_mapbox(
                df_council_valid.sample(n=min(8000, len(df_council_valid))),
                lat=lat_col, lon=lon_col,
                radius=12,
                center=dict(lat=40.7128, lon=-74.0060),
                zoom=10,
                height=640,
                mapbox_style="carto-darkmatter",
                color_continuous_scale=[
                    [0.0, "rgba(30,40,60,0)"],
                    [0.5, "rgba(200,50,50,0.6)"],
                    [1.0, "#D9383A"]
                ]
            )
            fig_council.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                coloraxis_colorbar=dict(
                    title=dict(text="Densidad", font=dict(color="#A0AEC0", size=11)),
                    tickfont=dict(color="#A0AEC0")
                )
            )
            st.plotly_chart(fig_council, use_container_width=True)
            fig_council = None  # ya renderizado

        # Puntos de frecuencia superpuestos sobre el coroplético
        if fig_council is not None:
            df_scatter = df_council_valid.sample(n=min(5000, len(df_council_valid)))
            colores_scatter = [
                COLOR_FOCO if d in top3_districts else "rgba(160, 174, 192, 0.35)"
                for d in df_scatter[council_col]
            ]

            fig_council.add_trace(go.Scattermapbox(
                lat=df_scatter[lat_col],
                lon=df_scatter[lon_col],
                mode='markers',
                marker=dict(size=4, color=colores_scatter, opacity=0.60),
                hovertemplate=(
                    "<b>Distrito %{customdata}</b><br>"
                    + ("%{text}<br>" if complaint_col else "")
                    + "<extra></extra>"
                ),
                text=df_scatter[complaint_col].astype(str) if complaint_col else None,
                customdata=df_scatter[council_col],
                name="Incidentes"
            ))

            fig_council.update_layout(
                mapbox=dict(
                    style="carto-darkmatter",
                    center=dict(lat=40.7128, lon=-74.0060),
                    zoom=10
                ),
                margin=dict(t=10, b=10, l=10, r=10),
                height=640,
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_council, use_container_width=True)

        # Top 5 distritos más críticos
        col_top, col_info = st.columns([0.4, 0.6])
        with col_top:
            top5 = df_freq.sort_values('frecuencia', ascending=False).head(5).reset_index(drop=True)
            top5.index += 1
            top5.columns = ['Distrito', 'Incidentes']
            st.markdown("**🔴 Top 5 Distritos — Mayor Carga**")
            st.dataframe(top5, use_container_width=True)
        with col_info:
            st.markdown(
                f"""
                <div style="padding: 14px; border-left: 4px solid {COLOR_FOCO}; background: rgba(217,56,58,0.06); border-radius:4px; margin-top: 6px;">
                    <span style="color:{COLOR_FOCO}; font-size:12px; font-weight:700;">LECTURA DEL MAPA</span><br>
                    <span style="color:#A0AEC0; font-size:13px;">
                        • <b style="color:white;">Zonas rojas intensas</b> = alta concentración de incidentes por distrito.<br>
                        • <b style="color:{COLOR_FOCO};">Puntos rojos</b> = incidentes en top-3 distritos críticos.<br>
                        • <b style="color:#718096;">Puntos grises</b> = resto de incidentes distribuidos.<br>
                        • Hover sobre cada zona para ver el número de reportes.
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.caption(f"Muestra aleatoria de 5,000 puntos · Columna detectada: '{council_col}'")