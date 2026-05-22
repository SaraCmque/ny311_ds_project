import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_dynamic_charts(df: pd.DataFrame):
    """Renderiza gráficas dinámicas avanzadas optimizadas para la detección de anomalías."""
    
    st.header("Análisis Visual Avanzado de Reportes (NYC 311)")
    
    if df is None or df.empty:
        st.warning("No hay datos disponibles en la capa Silver.")
        return
    
    df_work = df.copy()
    
    # Identificación e inferencia de columnas críticas
    date_col = next((col for col in df_work.columns if 'created' in col.lower() and 'date' in col.lower()), None)
    closed_col = next((col for col in df_work.columns if 'closed' in col.lower() and 'date' in col.lower()), None)
    complaint_col = next((col for col in df_work.columns if 'complaint' in col.lower() and 'type' in col.lower()), None)
    borough_col = next((col for col in df_work.columns if 'borough' in col.lower()), None)
    
    # Asegurar tipos de datos correctos para las 210k filas
    if date_col:
        df_work[date_col] = pd.to_datetime(df_work[date_col], errors='coerce')
    if closed_col:
        df_work[closed_col] = pd.to_datetime(df_work[closed_col], errors='coerce')

    # Paleta de colores estratégica
    COLOR_FOCO = "#D9383A"       # Rojo vibrante para anomalías
    COLOR_NEUTRO = "#4A5568"     # Gris slate para contexto histórico
    COLOR_FONDO_LIGERO = "rgba(0,0,0,0)"

    # ==========================================
    # ANÁLISIS 1: EFICIENCIA (TIEMPO DE RESOLUCIÓN)
    # ==========================================
    st.subheader("⏳ Anomalías en Tiempos de Respuesta por Categoría")
    st.write("Identificación de cuellos de botella: Categorías que exceden el tiempo promedio de cierre.")
    
    if date_col and closed_col and complaint_col:
        # Calcular tiempo de resolución en días
        df_work['tiempo_resolucion'] = (df_work[closed_col] - df_work[date_col]).dt.total_seconds() / 3600 / 24
        
        # Filtrar registros válidos (mayores a cero y no nulos)
        df_time = df_work[df_work['tiempo_resolucion'] >= 0].dropna(subset=['tiempo_resolucion'])
        
        if not df_time.empty:
            # Agrupar y sacar promedio por tipo de queja
            df_res_avg = df_time.groupby(complaint_col)['tiempo_resolucion'].mean().reset_index()
            df_res_avg = df_res_avg.sort_values(by='tiempo_resolucion', ascending=False).head(10)
            
            # El top 1 (peor tiempo) se convierte en FIGURA con color de alerta
            colores_tiempos = [COLOR_NEUTRO] * len(df_res_avg)
            colores_tiempos[0] = COLOR_FOCO # Al ser descendente, el índice 0 es el peor cuello de botella
            
            fig_perf = px.bar(df_res_avg, x='tiempo_resolucion', y=complaint_col, orientation='h')
            fig_perf.update_traces(marker_color=colores_tiempos, opacity=0.9)
            
            # Anotación explícita del peor *insight*
            peor_categoria = df_res_avg.iloc[0][complaint_col]
            peor_tiempo = df_res_avg.iloc[0]['tiempo_resolucion']
            
            fig_perf.update_layout(
                plot_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(showgrid=True, gridcolor="rgba(100,100,100,0.1)", title="Días Promedio para Cerrar Caso"),
                yaxis=dict(title_text=""),
                annotations=[
                    dict(
                        x=peor_tiempo, y=peor_categoria,
                        text=f"🚨 Alerta: <b>{peor_categoria}</b> tarda {peor_tiempo:.1f} días en promedio.",
                        showarrow=True, arrowhead=1, ax=-60, ay=30,
                        font=dict(color=COLOR_FOCO, size=11),
                        bgcolor="rgba(255,255,255,0.9)", bordercolor=COLOR_FOCO, borderwidth=1
                    )
                ]
            )
            st.plotly_chart(fig_perf, use_container_width=True)
            
    st.divider()

    # ==========================================
    # ANÁLISIS 2: MAPA DE CALOR TEMPORAL (PATRONES DE SATURACIÓN)
    # ==========================================
    st.subheader("🌡️ Matriz de Densidad: ¿Cuándo colapsa el servicio?")
    st.write("Detección de concentración de llamadas cruzando hora del día y día de la semana.")
    
    if date_col:
        # Extraer dimensiones de tiempo
        df_work['Hora'] = df_work[date_col].dt.hour
        df_work['Dia_Semana'] = df_work[date_col].dt.day_name()
        
        # Ordenar días correctamente
        dias_ordenados = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Crear matriz cruzada de conteos
        df_heatmap = df_work.groupby(['Dia_Semana', 'Hora']).size().reset_index(name='Cantidad')
        
        # Pivotar para estructura de mapa de calor nativo
        df_pivot = df_heatmap.pivot(index='Dia_Semana', columns='Hora', values='Cantidad').reindex(dias_ordenados)
        
        # Paleta secuencial limpia: Fondo oscuro a punto caliente vibrante
        fig_heat = px.imshow(
            df_pivot,
            labels=dict(x="Hora del Día (00:00 - 23:00)", y="Día de la Semana", color="Reportes"),
            x=df_pivot.columns,
            y=df_pivot.index,
            color_continuous_scale=["#2D3748", "#4A5568", "#CBD5E0", COLOR_FOCO] # Escala personalizada hacia el rojo
        )
        
        fig_heat.update_layout(
            plot_bgcolor=COLOR_FONDO_LIGERO,
            colorcontinuousaxis=dict(showscale=True)
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    # ==========================================
    # ANÁLISIS 3: RELACIÓN DE VOLUMEN (SCATTER DE DISTRITOS)
    # ==========================================
    st.subheader("🎯 Concentración de Carga por Localización")
    
    if borough_col and complaint_col:
        col_c1, col_c2 = st.columns([2, 1])
        
        with col_c1:
            # Cruzar volumen de reportes con variedad de quejas únicas por distrito
            df_borough_an = df_work.groupby(borough_col).agg(
                Total_Reportes=(complaint_col, 'count'),
                Tipos_Unicos_Queja=(complaint_col, 'nunique')
            ).reset_index()
            
            # Destacar visualmente a Brooklyn (Alta vibrancia) frente al resto (Neutros)
            colores_scatter = [
                COLOR_FOCO if b == "BROOKLYN" else COLOR_NEUTRO 
                for b in df_borough_an[borough_col]
            ]
            
            fig_scat = px.scatter(
                df_borough_an, 
                x='Total_Reportes', 
                y='Tipos_Unicos_Queja',
                text=borough_col,
                size='Total_Reportes',
                size_max=30
            )
            
            fig_scat.update_traces(
                marker=dict(color=colores_scatter, line=dict(width=1, color='white')),
                textposition='top center'
            )
            
            fig_scat.update_layout(
                plot_bgcolor=COLOR_FONDO_LIGERO,
                xaxis=dict(showgrid=True, gridcolor="rgba(100,100,100,0.1)", title="Volumen Total de Incidentes"),
                yaxis=dict(showgrid=True, gridcolor="rgba(100,100,100,0.1)", title="Diversidad de Problemas (Tipos Únicos)")
            )
            st.plotly_chart(fig_scat, use_container_width=True)
            
        with col_c2:
            st.markdown("#### Insight de Distribución")
            st.info(
                "Este cuadrante correlaciona la masa crítica de datos con la complejidad operativa. "
                "**Brooklyn** no solo lidera de forma aislada en volumen total, sino que "
                "demanda una diversificación casi absoluta de respuestas técnicas, convirtiéndose en el "
                "núcleo de riesgo para los SLAs de la ciudad."
            )