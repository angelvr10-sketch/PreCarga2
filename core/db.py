"""core/db.py — Base de datos Supabase para metadatos de solicitudes."""
import os
import re
from datetime import datetime
from core.supabase_db import _get, _post, _delete, _patch, HAS_HTTPX


def normalizar_fecha_iso(valor) -> str:
    """Convierte fechas sueltas a ISO yyyy-mm-dd (dd/mm/yyyy, dd-mm-yyyy, ISO...)."""
    if not valor:
        return ""
    s = str(valor).strip()[:10]
    m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", s)
    if m:
        d, mes, anio = m.groups()
        if 1 <= int(d) <= 31 and 1 <= int(mes) <= 12:
            return f"{anio}-{int(mes):02d}-{int(d):02d}"
        return s
    if re.match(r"^\d{4}", s):
        partes = re.split(r"[/\-]", s)
        if len(partes) == 3 and 1 <= int(partes[1]) <= 12:
            return f"{partes[0]}-{int(partes[1]):02d}-{int(partes[2]):02d}"
    return s


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
    fecha_llegada = normalizar_fecha_iso(personal_sube[0]["llegada"]) if personal_sube else ""

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
        "destinohosp": info.get("destinohosp") or "",
        "elepep": info.get("elepep") or "",
        "progpre": info.get("progpre") or "",
        "cge": info.get("cge") or "",
        "cta": info.get("cta") or "",
        "pos": info.get("pos") or "",
        "nombre_solicita": info.get("nombre_solicita") or "",
        "ficha_solicita": info.get("ficha_solicita") or "",
        "nombre_autoriza": info.get("nombre_autoriza") or "",
        "ficha_autoriza": info.get("ficha_autoriza") or "",
        "razonsocial": info.get("razonsocial") or "",
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


def _obtener_personal(numero: str, tipo: str) -> list[dict]:
    rows = _get("solicitudes", filters={"numero": f"eq.{numero}"}, select="id")
    if not rows:
        return []
    sol_id = rows[0]["id"]
    pers = _get("personal", filters={"solicitud_id": f"eq.{sol_id}", "tipo": f"eq.{tipo}"})
    return [dict(r) for r in pers]


def obtener_personal_sube(numero: str) -> list[dict]:
    return _obtener_personal(numero, "sube")


def obtener_personal_baja_db(numero: str) -> list[dict]:
    pers = _obtener_personal(numero, "baja")
    return [{"rfc": p.get("rfc", ""), "nombre": p.get("nombre", ""),
             "transporte": p.get("transporte", "")} for p in pers]


def obtener_personal_baja(numero: str) -> list[dict]:
    return _obtener_personal(numero, "baja")


def eliminar_solicitud(numero: str):
    # Buscar id
    rows = _get("solicitudes", filters={"numero": f"eq.{numero}"}, select="id")
    if rows:
        sol_id = rows[0]["id"]
        # Cascade delete en personal via RLS o trigger en Supabase
        _delete("personal", {"solicitud_id": f"eq.{sol_id}"})
        _delete("solicitudes", {"id": f"eq.{sol_id}"})
