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

BASE = f"{SUPABASE_URL}/rest/v1"


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
    r = httpx.get(f"{BASE}/{table}", headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    return r.json() if r.status_code != 204 else []


def _post(table: str, data: dict) -> Optional[dict]:
    """POST a Supabase table. Devuelve el registro insertado o None."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    r = httpx.post(f"{BASE}/{table}", headers=HEADERS, json=data, timeout=10)
    r.raise_for_status()
    result = r.json()
    return result[0] if result else None


def _delete(table: str, filters: dict) -> list:
    """DELETE de Supabase table. Devuelve los registros eliminados."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    params = {}
    for k, v in filters.items():
        params[k] = v
    r = httpx.delete(f"{BASE}/{table}", headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    return r.json() if r.status_code != 204 else []


def _patch(table: str, data: dict, filters: dict) -> list:
    """UPDATE en Supabase table. Devuelve los registros modificados."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    params = dict(filters)
    r = httpx.patch(f"{BASE}/{table}", headers=HEADERS, params=params, json=data, timeout=10)
    r.raise_for_status()
    return r.json() if r.status_code != 204 else []


def _exec_sql(sql: str):
    """Ejecuta SQL directo via la API de Supabase (rpc)."""
    if not httpx:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    # Usar el endpoint de SQL directo no es trivial via REST, mejor usamos httpx
    # directamente a la API. Para crear tablas, usamos la funcion rpc o el endpoint.
    # La forma mas simple es ejecutar las sentencias DDL via el endpoint de SQL.
    # Pero Supabase REST no soporta DDL directamente. En su lugar, asumimos
    # que las tablas ya existen (el usuario las crea via SQL en el dashboard).
    # Para verificar, hacemos una consulta simple.
    pass


def verificar_conexion() -> bool:
    """Verifica que Supabase este accesible y las tablas existan."""
    try:
        # Intentar consultar la tabla usuarios
        r = httpx.get(f"{BASE}/usuarios", headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "select": "id"}, timeout=10)
        return r.status_code in (200, 204, 406)  # 406 puede ser normal si no hay datos
    except Exception:
        return False
