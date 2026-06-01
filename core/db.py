"""core/db.py — Base de datos Supabase para metadatos de solicitudes."""
import os
from datetime import datetime
from core.supabase_db import _get, _post, _delete, _patch, HAS_HTTPX


# ──────────────────────────────────────────────────────────────
#  Inicializacion
# ──────────────────────────────────────────────────────────────

def init_solicitudes_db():
    """Verifica conexion a Supabase (las tablas se crean via SQL en el dashboard)."""
    if not HAS_HTTPX:
        raise RuntimeError("httpx no esta instalado. pip install httpx")
    # Intentar consultar la tabla solicitudes para verificar que existe
    try:
        _get("solicitudes", select="id", limit=1)
        print("Tablas de solicitudes verificadas en Supabase")
    except Exception as e:
        print(f"WARNING: No se pudo verificar la tabla solicitudes en Supabase: {e}")


# ──────────────────────────────────────────────────────────────
#  Escritura
# ──────────────────────────────────────────────────────────────

def guardar_solicitud(info: dict, personal_sube: list, personal_baja: list,
                      archivo: str) -> int:
    """
    Inserta o reemplaza una solicitud con todo su personal.
    Devuelve el id de la solicitud.
    """
    procesado = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_llegada = personal_sube[0]["llegada"][:10] if personal_sube else ""

    # Buscar si ya existe
    existentes = _get("solicitudes", filters={"numero": f"eq.{info.get('solicitud', 'SIN_NUM')}"},
                      select="id")

    if existentes:
        sol_id = existentes[0]["id"]
        # Borrar personal existente
        _delete("personal", {"solicitud_id": f"eq.{sol_id}"})
        # Borrar solicitud
        _delete("solicitudes", {"id": f"eq.{sol_id}"})

    # Insertar nueva solicitud
    nueva_sol = _post("solicitudes", {
        "numero": info.get("solicitud", "SIN_NUM"),
        "compania": info.get("compania_corta", info.get("razonsocial", "")),
        "n_personas": len(personal_sube),
        "fecha_llegada": fecha_llegada,
        "transporte": info.get("transporte", ""),
        "tipo": info.get("tipo", ""),
        "contrato": info.get("contrato", ""),
        "activo_a": info.get("activoA") or "",
        "activo_s": info.get("activoS") or "",
        "tiene_bajas": bool(personal_baja),
        "n_bajas": len(personal_baja),
        "archivo": archivo,
        "procesado": procesado,
    })

    if not nueva_sol:
        raise RuntimeError("No se pudo crear la solicitud")

    sol_id = nueva_sol["id"]

    # Personal que sube
    for p in personal_sube:
        _post("personal", {
            "solicitud_id": sol_id,
            "tipo": "sube",
            "rfc": p.get("rfc", ""),
            "nombre": p.get("nombre", ""),
            "libreta": p.get("libreta", ""),
            "vigencia": p.get("vigencia", ""),
            "llegada": p.get("llegada", ""),
            "salida": p.get("salida", ""),
            "dias": p.get("dias", ""),
            "transporte": info.get("transporte", ""),
        })

    # Personal que baja
    for p in personal_baja:
        _post("personal", {
            "solicitud_id": sol_id,
            "tipo": "baja",
            "rfc": p.get("rfc", ""),
            "nombre": p.get("nombre", ""),
            "libreta": p.get("libreta", ""),
            "vigencia": p.get("vigencia", ""),
            "llegada": p.get("llegada", ""),
            "salida": p.get("salida", ""),
            "dias": p.get("dias", ""),
            "transporte": info.get("transporte", ""),
        })

    return sol_id


# ──────────────────────────────────────────────────────────────
#  Lectura rapida
# ──────────────────────────────────────────────────────────────

def listar_solicitudes_db(limit: int = 200) -> list[dict]:
    """
    Devuelve solicitudes ordenadas por fecha de llegada DESC.
    """
    rows = _get("solicitudes",
                select="numero,compania,n_personas,fecha_llegada,transporte,tiene_bajas,n_bajas,archivo,procesado",
                order="fecha_llegada.desc,procesado.desc",
                limit=limit)
    return [dict(r) for r in rows]


def listar_bajas_db() -> list[dict]:
    """Devuelve solicitudes que tienen personal de baja."""
    rows = _get("solicitudes",
                select="numero,compania,n_bajas",
                filters={"tiene_bajas": "eq.true"},
                order="procesado.desc")
    return [dict(r) for r in rows]


def obtener_solicitud(numero: str) -> dict | None:
    rows = _get("solicitudes", filters={"numero": f"eq.{numero}"})
    return dict(rows[0]) if rows else None


def obtener_personal_sube(numero: str) -> list[dict]:
    rows = _get("solicitudes", filters={"numero": f"eq.{numero}"}, select="id")
    if not rows:
        return []
    sol_id = rows[0]["id"]
    pers = _get("personal", filters={"solicitud_id": f"eq.{sol_id}", "tipo": "eq.sube"})
    return [dict(r) for r in pers]


def obtener_personal_baja_db(numero: str) -> list[dict]:
    rows = _get("solicitudes", filters={"numero": f"eq.{numero}"}, select="id")
    if not rows:
        return []
    sol_id = rows[0]["id"]
    pers = _get("personal", filters={"solicitud_id": f"eq.{sol_id}", "tipo": "eq.baja"},
                select="rfc,nombre,transporte")
    return [dict(r) for r in pers]


def eliminar_solicitud(numero: str):
    # Buscar id
    rows = _get("solicitudes", filters={"numero": f"eq.{numero}"}, select="id")
    if rows:
        sol_id = rows[0]["id"]
        # Cascade delete en personal via RLS o trigger en Supabase
        _delete("personal", {"solicitud_id": f"eq.{sol_id}"})
        _delete("solicitudes", {"id": f"eq.{sol_id}"})
