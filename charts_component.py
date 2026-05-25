import streamlit as st
import pandas as pd
import plotly.express as px
from s3_utils import load_from_s3

def render_dynamic_charts():
    prefix_gold = "gold/enhanced_for_streamlit_eda/"
    df_raw = load_from_s3(prefix=prefix_gold)
    
    if df_raw is None or df_raw.empty:
        st.error("No se pudieron cargar los datos.")
        return

    # 1. PREPARACIÓN DE DATOS (Foco en Negligencia)
    df_overdue = df_raw[df_raw['is_overdue_official'] == 1].copy()
    
    st.header("🏢 Desglose de Responsabilidad Financiera por Agencia")
    st.markdown("""
    Este reporte detalla el **Pasivo Contingente**. Representa el costo acumulado de los reclamos 
    que superaron el tiempo legal de respuesta, clasificados por la agencia responsable.
    """)

    # 2. CÁLCULO POR AGENCIA (Bottom-Up)
    # Agrupamos para obtener la métrica por cada departamento
    df_agency_summary = df_overdue.groupby('Agency').agg(
        casos_vencidos=('Unique Key', 'count'),
        costo_promedio_indemnizacion=('avg_negligence_cost', 'first'),
        riesgo_total_usd=('estimated_liability_usd', 'sum')
    ).reset_index()

    # Ordenar por el riesgo más alto (Ingeniería de la Atención)
    df_agency_summary = df_agency_summary.sort_values('riesgo_total_usd', ascending=False)

    # 3. VISUALIZACIÓN: TABLA DE AUDITORÍA
    st.subheader("1. Matriz de Riesgo por Departamento")
    
    # Formatear para visualización
    df_table = df_agency_summary.copy()
    df_table['riesgo_total_usd'] = df_table['riesgo_total_usd'].apply(lambda x: f"${x:,.0f}")
    df_table['costo_promedio_indemnizacion'] = df_table['costo_promedio_indemnizacion'].apply(lambda x: f"${x:,.0f}")
    
    st.table(df_table.rename(columns={
        'Agency': 'Agencia',
        'casos_vencidos': 'Casos fuera de SLA',
        'costo_promedio_indemnizacion': 'Costo x Negligencia',
        'riesgo_total_usd': 'Pasivo Total (USD)'
    }))

    # 4. GRÁFICA DE DOMINANCIA (Treemap - Ideal para ver quién aporta más al total)
    st.subheader("2. Distribución del Riesgo de Ciudad")
    fig_tree = px.treemap(
        df_agency_summary, 
        path=['Agency'], 
        values='riesgo_total_usd',
        title="Proporción del Pasivo Total por Agencia",
        color='riesgo_total_usd',
        color_continuous_scale='Reds'
    )
    st.plotly_chart(fig_tree, use_container_width=True)

    st.divider()

    # 5. EL GRAN TOTAL (Cierre del Storytelling)
    st.subheader("3. Consolidado de Riesgo Legal (Total NYC)")
    
    total_casos_vencidos = df_agency_summary['casos_vencidos'].sum()
    gran_pasivo_total = df_agency_summary['riesgo_total_usd'].sum()
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total Global de Casos Vencidos", f"{total_casos_vencidos:,}")
    with c2:
        # Resaltamos el total con color rojo de alerta
        st.markdown(f"""
            <div style="background-color:#C0292B; padding:20px; border-radius:10px; text-align:center;">
                <h2 style="color:white; margin:0;">PASIVO TOTAL ESTIMADO</h2>
                <h1 style="color:white; margin:0;">${gran_pasivo_total/1e6:.1f} Millones USD</h1>
            </div>
        """, unsafe_allow_html=True)

    st.success(f"⚠️ **Conclusión de Negocio:** La ineficiencia en los tiempos de respuesta de la agencia **{df_agency_summary.iloc[0]['Agency']}** es el principal motor del riesgo financiero, aportando el **{(df_agency_summary.iloc[0]['riesgo_total_usd']/gran_pasivo_total)*100:.1f}%** del pasivo total proyectado.")
