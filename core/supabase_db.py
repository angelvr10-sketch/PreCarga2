"""core/supabase_db.py — Capa de acceso a Supabase (PostgreSQL)

Reemplaza las bases de datos SQLite (usuarios.db, solicitudes.db)
por llamadas a la API REST de Supabase via httpx.
"""
import os
import time
import urllib.parse
from datetime import datetime
from typing import Optional
from pathlib import Path

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    httpx = None

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Headers para las peticiones REST
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

BASE = f"{SUPABASE_URL}/rest/v1"

# Configuramos un timeout más generoso para evitar errores de handshake en redes inestables
TIMEOUT_CONFIG = 30.0 
MAX_RETRIES = 3

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _request_with_retry(method, url, **kwargs):
    """Wrapper para realizar peticiones con reintentos en caso de Timeout o SSL Errors."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            # Usamos un timeout explícito
            response = httpx.request(method, url, timeout=TIMEOUT_CONFIG, **kwargs)
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            last_exception = e
            time.sleep(1 * (attempt + 1)) # Espera exponencial simple
    
    raise last_exception

# ──────────────────────────────────────────────────────────────
#  Funciones de bajo nivel para llamadas REST
# ──────────────────────────────────────────────────────────────

def _get(table: str, select: str = "*", filters: Optional[dict] = None,
         order: Optional[str] = None, limit: Optional[int] = None) -> list:
    """GET a Supabase table. Devuelve lista de dicts."""
    params = {"select": select}
    if filters:
        for k, v in filters.items():
            params[k] = v
    if order:
        params["order"] = order
    if limit:
        params["limit"] = limit
    
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry("GET", url, headers=HEADERS, params=params)
        return r.json() if r.status_code != 204 else []
    except Exception as e:
        print(f"\n[DB ERROR GET] Table: {table} | URL: {url} | Params: {params}")
        print(f"Error: {e}")
        raise e

def _post(table: str, data: dict) -> Optional[dict]:
    """POST a Supabase table. Devuelve el registro insertado o None."""
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry("POST", url, headers=HEADERS, json=data)
        result = r.json()
        return result[0] if result else None
    except Exception as e:
        print(f"\n[DB ERROR POST] Table: {table} | URL: {url} | Data: {data}")
        print(f"Error: {e}")
        raise e

def _delete(table: str, filters: dict) -> list:
    """DELETE de Supabase table. Devuelve los registros eliminados."""
    params = {}
    for k, v in filters.items():
        params[k] = v
    
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry("DELETE", url, headers=HEADERS, params=params)
        return r.json() if r.status_code != 204 else []
    except Exception as e:
        print(f"\n[DB ERROR DELETE] Table: {table} | URL: {url} | Filters: {filters}")
        print(f"Error: {e}")
        raise e

def _patch(table: str, data: dict, filters: dict) -> list:
    """UPDATE en Supabase table. Devuelve los registros modificados."""
    params = dict(filters)
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry("PATCH", url, headers=HEADERS, params=params, json=data)
        return r.json() if r.status_code != 204 else []
    except Exception as e:
        print(f"\n[DB ERROR PATCH] Table: {table} | URL: {url} | Data: {data}")
        print(f"Error: {e}")
        raise e

def _exec_sql(sql: str):
    """Ejecuta SQL directo via la API de Supabase (rpc)."""
    pass

def verificar_conexion() -> bool:
    """Verifica que Supabase este accesible y las tablas existan."""
    try:
        # Petición simple para testear conexión
        _request_with_retry("GET", f"{BASE}/usuarios", headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}, params={"select": "id"})
        return True
    except Exception:
        return False

# ──────────────────────────────────────────────────────────────
#  Gestión de Compañías
# ──────────────────────────────────────────────────────────────

def leer_companias_supabase() -> list:
    """Obtiene todas las compañías desde Supabase."""
    # Retorno de lista de dicts con razon_social y nombre_corto
    return _get("companias")

def agregar_compania_supabase(razon_social: str, nombre_corto: str):
    """Agrega una nueva compañía a Supabase."""
    data = {
        "razon_social": razon_social,
        "nombre_corto": nombre_corto,
        "updated_at": _now()
    }
    return _post("companias", data)

def eliminar_compania_supabase(razon_social: str):
    """Elimina una compañía basada en su razón social."""
    return _delete("companias", {"razon_social": razon_social})

# ──────────────────────────────────────────────────────────────
#  Gestión de Activos
# ──────────────────────────────────────────────────────────────

def leer_activos_supabase() -> list:
    """Obtiene la lista de activos activos."""
    res = _get("activos", select="nombre")
    return [item["nombre"] for item in res]

def agregar_activo_supabase(nombre: str):
    """Agrega un nuevo activo."""
    return _post("activos", {"nombre": nombre})

def eliminar_activo_supabase(nombre: str):
    """Elimina un activo por nombre."""
    return _delete("activos", {"nombre": nombre})

# ──────────────────────────────────────────────────────────────
#  Funciones de Storage (Bucket)
# ──────────────────────────────────────────────────────────────

def upload_file_to_storage(bucket_name: str, file_path: Path, file_name: str):
    """Sube un archivo al Storage de Supabase usando PUT para asegurar reemplazo."""
    encoded_file_name = urllib.parse.quote(file_name)
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{encoded_file_name}"
    
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        upload_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/octet-stream"
        }
        
        r = _request_with_retry("PUT", url, headers=upload_headers, content=content)
        return r.json()
    except Exception as e:
        print(f"\n[STORAGE ERROR UPLOAD] File: {file_name} | Error: {e}")
        raise e

def get_public_url(bucket_name: str, file_name: str) -> str:
    """Retorna la URL pública de un archivo en el bucket."""
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{file_name}"

def download_file_from_storage(bucket_name: str, file_name: str) -> bytes:
    """Descarga el contenido de un archivo desde Supabase Storage."""
    encoded_file_name = urllib.parse.quote(file_name)
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{encoded_file_name}"
    try:
        r = _request_with_retry("GET", url, headers=HEADERS)
        return r.content
    except Exception as e:
        print(f"\n[STORAGE ERROR DOWNLOAD] File: {file_name} | Error: {e}")
        raise e

def delete_file_from_storage(bucket_name: str, file_name: str):
    """Elimina un archivo del Storage de Supabase."""
    encoded_file_name = urllib.parse.quote(file_name)
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{encoded_file_name}"
    try:
        r = _request_with_retry("DELETE", url, headers=HEADERS)
        return r.json()
    except Exception as e:
        print(f"\n[STORAGE ERROR DELETE] File: {file_name} | Error: {e}")
        raise e
