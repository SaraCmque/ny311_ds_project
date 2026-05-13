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
def load_from_s3(prefix: str, bucket: str = "proyecto-ny311") -> pd.DataFrame | None:
    """Carga datos desde S3 de forma genérica (CSV, Parquet)."""
    try:
        s3 = get_s3_client()
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = response.get('Contents', [])
        
        if not objects:
            return None
        
        files = [obj['Key'] for obj in objects if any(obj['Key'].endswith(ext) for ext in ['.csv', '.parquet'])]
        
        if not files:
            return None
        
        part_files = sorted([f for f in files if 'part-' in os.path.basename(f)])
        candidates = part_files if part_files else sorted(files)
        
        if len(candidates) > 1:
            dfs = []
            for selected in candidates:
                obj = s3.get_object(Bucket=bucket, Key=selected)
                body = io.BytesIO(obj['Body'].read())
                if selected.endswith('.parquet'):
                    dfs.append(pd.read_parquet(body))
                else:
                    dfs.append(pd.read_csv(body))
            return pd.concat(dfs, ignore_index=True)

        selected = candidates[0]
        obj = s3.get_object(Bucket=bucket, Key=selected)
        body = io.BytesIO(obj['Body'].read())
        
        if selected.endswith('.parquet'):
            return pd.read_parquet(body)
        return pd.read_csv(body)
            
    except Exception as e:
        st.error(f"Error cargando datos de {prefix}: {e}")
        return None
