"""core/supabase_db.py — Capa de acceso a Supabase (PostgreSQL)

Reemplaza las bases de datos SQLite (usuarios.db, solicitudes.db)
por llamadas a la API REST de Supabase via httpx.
"""
import os
from datetime import datetime
from typing import Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    httpx = None

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Headers para las peticiones REST
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

BASE = SUPABASE_URL


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ──────────────────────────────────────────────────────────────
#  Funciones de bajo nivel para llamadas REST
# ──────────────────────────────────────────────────────────────

def _get(table: str, select: str = "*", filters: Optional[dict] = None,
         order: Optional[str] = None, limit: Optional[int] = None) -> list:
    """GET a Supabase table. Devuelve lista de dicts."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
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
        r = httpx.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json() if r.status_code != 204 else []
    except Exception as e:
        print(f"\n[DB ERROR GET] Table: {table} | URL: {url} | Params: {params}")
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise e


def _post(table: str, data: dict) -> Optional[dict]:
    """POST a Supabase table. Devuelve el registro insertado o None."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    
    url = f"{BASE}/{table}"
    try:
        r = httpx.post(url, headers=HEADERS, json=data, timeout=10)
        r.raise_for_status()
        result = r.json()
        return result[0] if result else None
    except Exception as e:
        print(f"\n[DB ERROR POST] Table: {table} | URL: {url} | Data: {data}")
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise e


def _delete(table: str, filters: dict) -> list:
    """DELETE de Supabase table. Devuelve los registros eliminados."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    params = {}
    for k, v in filters.items():
        params[k] = v
    
    url = f"{BASE}/{table}"
    try:
        r = httpx.delete(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json() if r.status_code != 204 else []
    except Exception as e:
        print(f"\n[DB ERROR DELETE] Table: {table} | URL: {url} | Filters: {filters}")
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise e


def _patch(table: str, data: dict, filters: dict) -> list:
    """UPDATE en Supabase table. Devuelve los registros modificados."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    params = dict(filters)
    
    url = f"{BASE}/{table}"
    try:
        r = httpx.patch(url, headers=HEADERS, params=params, json=data, timeout=10)
        r.raise_for_status()
        return r.json() if r.status_code != 204 else []
    except Exception as e:
        print(f"\n[DB ERROR PATCH] Table: {table} | URL: {url} | Data: {data}")
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise e


def _exec_sql(sql: str):
    """Ejecuta SQL directo via la API de Supabase (rpc)."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    pass


def verificar_conexion() -> bool:
    """Verifica que Supabase este accesible y las tablas existan."""
    try:
        r = httpx.get(f"{BASE}/usuarios", headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "select": "id"}, timeout=10)
        return r.status_code in (200, 204, 406)
    except Exception:
        return False
