import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_dynamic_charts(df: pd.DataFrame):
    """
    Renderiza gráficas dinámicas optimizadas con etiquetado explícito de ejes.
    """
    st.header("Análisis Visual de Reportes (NYC 311)")
    
    if df is None or df.empty:
        st.warning("No hay datos disponibles.")
        return
    
    df_work = df.copy()
    date_col = next((col for col in df_work.columns if 'created' in col.lower() and 'date' in col.lower()), None)
    closed_col = next((col for col in df_work.columns if 'closed' in col.lower() and 'date' in col.lower()), None)
    complaint_col = next((col for col in df_work.columns if 'complaint' in col.lower() and 'type' in col.lower()), None)
    borough_col = next((col for col in df_work.columns if 'borough' in col.lower()), None)
    
    if date_col:
        df_work[date_col] = pd.to_datetime(df_work[date_col], errors='coerce')
    if closed_col:
        df_work[closed_col] = pd.to_datetime(df_work[closed_col], errors='coerce')
    
    col_a, col_b = st.columns(2)
    COLOR_FOCO = "#D9383A"       
    COLOR_NEUTRO = "#4A5568"     
    COLOR_FONDO_LIGERO = "rgba(0,0,0,0)"

    # 1. TOP 10 QUEJAS (Gráfico de Barras Horizontal)
    with col_a:
        st.subheader("Top 10 Quejas Principalmente Críticas")
        if complaint_col:
            top_complaints = df_work[complaint_col].value_counts().head(10).reset_index()
            top_complaints.columns = ['Tipo', 'Cantidad']
            colores_quejas = [COLOR_NEUTRO] * len(top_complaints)
            colores_quejas[-1] = COLOR_FOCO  
            
            fig = px.bar(top_complaints, x='Cantidad', y='Tipo', orientation='h')
            fig.update_traces(marker_color=colores_quejas, marker_line_color=colores_quejas, opacity=0.85)
            
            # CAMBIO: Configuración explícita de títulos de ejes
            fig.update_layout(
                showlegend=False, 
                plot_bgcolor=COLOR_FONDO_LIGERO, 
                xaxis=dict(
                    showgrid=False, 
                    title=dict(text="Cantidad de Reportes", font=dict(size=12, color="#A0AEC0"))
                ), 
                yaxis=dict(
                    categoryorder='total ascending', 
                    title=dict(text="Tipo de Incidente", font=dict(size=12, color="#A0AEC0"))
                )
            )
            st.plotly_chart(fig, use_container_width=True)

    # 2. DISTRIBUCIÓN POR DISTRITO (Dona / Pie) - No lleva ejes pero se ajusta layout
    with col_b:
        st.subheader("Distribución por Distrito (Volumen de Carga)")
        if borough_col:
            borough_dist = df_work[borough_col].value_counts().reset_index()
            borough_dist.columns = ['Distrito', 'Total']
            borough_dist = borough_dist.sort_values(by='Total', ascending=True)
            
            fig = px.pie(borough_dist, values='Total', names='Distrito', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(plot_bgcolor=COLOR_FONDO_LIGERO, paper_bgcolor=COLOR_FONDO_LIGERO)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 3. EVOLUCIÓN TEMPORAL DE INCIDENTES (Gráfico de Líneas)
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
        
        fig.add_trace(go.Scatter(x=[row_max['Fecha']], y=[row_max['Total']], mode='markers+text', marker=dict(color=COLOR_FOCO, size=12, line=dict(width=2, color='white')), text=[f"Pico Máximo: {row_max['Total']}"], textposition="top center", textfont=dict(color="white", size=12)))
        fig.add_trace(go.Scatter(x=[row_min['Fecha']], y=[row_min['Total']], mode='markers+text', marker=dict(color="#63B3ED", size=10, line=dict(width=2, color='white')), text=[f"Mínimo: {row_min['Total']}"], textposition="bottom center", textfont=dict(color="#A0AEC0", size=11)))
        
        # CAMBIO: Forzar la visibilidad y nombre exacto de los ejes X e Y
        fig.update_layout(
            showlegend=False, 
            plot_bgcolor=COLOR_FONDO_LIGERO, 
            xaxis=dict(
                showgrid=False, 
                title=dict(text="Línea de Tiempo (Días)", font=dict(size=12, color="#A0AEC0"))
            ), 
            yaxis=dict(
                showgrid=True, 
                gridcolor="rgba(200,200,200,0.1)", 
                title=dict(text="Frecuencia Diaria de Casos", font=dict(size=12, color="#A0AEC0"))
            )
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 4. EFICIENCIA OPERATIVA (SLAs)
    st.subheader("⏳ Eficiencia y Cuellos de Botella en Respuesta (SLAs)")
    st.write("Análisis del tiempo promedio requerido para resolver y cerrar incidentes por categoría.")
    
    if date_col and closed_col and complaint_col:
        df_work['dias_resolucion'] = (df_work[closed_col] - df_work[date_col]).dt.total_seconds() / 86400
        df_sla = df_work[df_work['dias_resolucion'] >= 0].dropna(subset=['dias_resolucion'])
        
        if not df_sla.empty:
            df_sla_avg = df_sla.groupby(complaint_col)['dias_resolucion'].mean().reset_index()
            df_sla_avg = df_sla_avg.sort_values(by='dias_resolucion', ascending=True).head(10)
            
            colores_sla = [COLOR_NEUTRO] * len(df_sla_avg)
            colores_sla[-1] = COLOR_FOCO  
            
            fig_sla = px.bar(df_sla_avg, x='dias_resolucion', y=complaint_col, orientation='h')
            fig_sla.update_traces(marker_color=colores_sla, opacity=0.9)
            
            peor_cat = df_sla_avg.iloc[-1][complaint_col]
            peor_dia = df_sla_avg.iloc[-1]['dias_resolucion']
            
            # CAMBIO: Ejes titulados con precisión milimétrica para control operativo
            fig_sla.update_layout(
                plot_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="rgba(100,100,100,0.1)", 
                    title=dict(text="Días Promedio de Cierre", font=dict(size=12, color="#A0AEC0"))
                ),
                yaxis=dict(
                    title=dict(text="Categoría de Queja", font=dict(size=12, color="#A0AEC0"))
                ),
                xaxis_range=[0, peor_dia * 1.3],
                annotations=[dict(
                    x=peor_dia, y=peor_cat, 
                    text=f"⚠️ <b>RETRASO ANORMAL DETECTADO</b><br>La categoría <i>{peor_cat}</i><br>rompe los SLAs con {peor_dia:.1f} días promedio.", 
                    showarrow=True, arrowhead=2, arrowcolor=COLOR_FOCO, ax=80, ay=0, 
                    font=dict(color=COLOR_FOCO, size=11), bgcolor="rgba(255, 255, 255, 0.95)", bordercolor=COLOR_FOCO, borderwidth=1
                )]
            )
            st.plotly_chart(fig_sla, use_container_width=True)

    st.divider()

    # 5. CONCENTRACIÓN GEOGRÁFICA
    lat_col = next((col for col in df_work.columns if col.lower() == 'latitude'), None)
    lon_col = next((col for col in df_work.columns if col.lower() == 'longitude'), None)
    if lat_col and lon_col:
        st.subheader("Concentración Geográfica de Incidentes")
        df_map = df_work.dropna(subset=[lat_col, lon_col]).sample(n=min(5000, len(df_work)))
        fig = px.scatter_mapbox(df_map, lat=lat_col, lon=lon_col, hover_name=complaint_col if complaint_col else None, zoom=10, height=600, mapbox_style="carto-darkmatter")
        if borough_col:
            colores_mapa = [COLOR_FOCO if b == "BROOKLYN" else "#718096" for b in df_map[borough_col]]
            fig.update_traces(marker=dict(color=colores_mapa, size=4, opacity=0.6))
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)