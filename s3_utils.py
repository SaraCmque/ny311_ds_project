import os
import streamlit as st
import pandas as pd
import boto3
import io

@st.cache_resource
def get_s3_client():
    """Obtiene cliente S3 con credenciales de Streamlit secrets."""
    return boto3.client(
        's3',
        aws_access_key_id=st.secrets["aws"]["access_key"],
        aws_secret_access_key=st.secrets["aws"]["secret_key"],
        aws_session_token=st.secrets["aws"].get("session_token"),
        region_name=st.secrets["aws"]["region"]
    )

@st.cache_data(ttl=3600)
def load_from_s3(prefix: str, bucket: str = "proyect-ny311") -> pd.DataFrame | None:
    """Carga datos desde S3 evitando operaciones HeadObject automáticas de pandas."""
    try:
        s3 = get_s3_client()
        # Asegurar que el prefijo termine en / para listar correctamente
        if not prefix.endswith('/'):
            prefix += '/'
            
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = response.get('Contents', [])
        
        if not objects:
            st.warning(f"No se encontraron objetos en s3://{bucket}/{prefix}")
            return None
        
        # Filtrar solo archivos de datos (ignorar carpetas y archivos de éxito de Spark)
        files = [obj['Key'] for obj in objects if obj['Key'].endswith('.parquet') or obj['Key'].endswith('.csv')]
        files = [f for f in files if not f.endswith('_SUCCESS')]

        if not files:
            st.warning("No se encontraron archivos .parquet o .csv válidos.")
            return None
        
        dfs = []
        for key in files:
            # Descargar el objeto a memoria usando boto3 (usa tus credenciales de secrets)
            obj = s3.get_object(Bucket=bucket, Key=key)
            content = obj['Body'].read()
            buffer = io.BytesIO(content)
            
            if key.endswith('.parquet'):
                # Leemos el buffer, NO la ruta S3 string. Esto evita el error de permisos.
                dfs.append(pd.read_parquet(buffer, engine='pyarrow'))
            else:
                dfs.append(pd.read_csv(buffer))
        
        if not dfs:
            return None
            
        return pd.concat(dfs, ignore_index=True)
            
    except Exception as e:
        st.error(f"Error cargando datos de {prefix}: {str(e)}")
        return None


@st.cache_data(ttl=3600)
def load_parquet_from_s3(key: str, bucket: str = "proyect-ny311") -> pd.DataFrame | None:
    """Carga un único archivo .parquet desde S3 usando la clave exacta."""
    try:
        s3 = get_s3_client()
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj['Body'].read()
        return pd.read_parquet(io.BytesIO(content), engine='pyarrow')
    except Exception as e:
        st.warning(f"No se encontró objeto en s3://{bucket}/{key}: {str(e)}")
        return None
