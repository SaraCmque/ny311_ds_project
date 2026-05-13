# NYC 311: Dashboard de Calidad de Datos y Estadísticas

Dashboard interactivo para el análisis de calidad de datos y estadísticas de reportes del servicio NYC 311. Proporciona una visión integral de la limpieza de datos (Bronze → Silver -> Gold), análisis exploratorio y visualizaciones dinámicas del dataset completo.

## 🔗 Acceso

**Disponible en:** [https://ny311dsproyect.streamlit.app/](https://ny311dsproyect.streamlit.app/)

## Características

- **Control de Calidad**: Análisis de duplicados, valores nulos y outliers (Bronze vs Silver)
- **Estadísticas Detalladas**: Resumen exploratorio por columna (moda, rango, distribución)
- **Gráficas Dinámicas**: 
  - Top 10 tipos de quejas
  - Distribución por distrito
  - Evolución temporal de reportes
  - Mapa de incidentes (5,000 puntos de muestra)

## 🛠️ Stack Tecnológico

- **Frontend**: Streamlit
- **Processing**: Python + Pandas + Plotly
- **Storage**: AWS S3
- **Data Pipeline**: AWS Glue

## 📁 Estructura del Proyecto

```
ny311_ds_proyect/
├── main.py                 # Punto de entrada
├── s3_utils.py            # Utilidades para cargar datos de S3
├── quality_component.py   # Componente de control de calidad
├── eda_component.py       # Componente de análisis exploratorio
├── charts_component.py    # Componente de gráficas dinámicas
└── requirements.txt       # Dependencias
```

## 🚀 Cómo ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run main.py
```

## 📝 Notas

- Las gráficas dinámicas usan todos los datos del dataset (200k+ registros)
- El mapa de incidentes muestra una muestra de hasta 5,000 puntos para optimizar el rendimiento
- Los datos se actualizan cada 1 hora (TTL en caché)