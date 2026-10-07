"""routers/api_data.py — Endpoints JSON de datos para el frontend SPA"""
import math
from datetime import datetime, date, timedelta
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core import listar_solicitudes_xlsx
from core.supabase_db import (
    leer_companias_supabase, agregar_compania_supabase, eliminar_compania_supabase,
    leer_activos_supabase, agregar_activo_supabase, eliminar_activo_supabase,
    _get, _count_rows,
)
from core.db import listar_bajas_db, listar_solicitudes_db
from core.auth import get_user_from_token, listar_usuarios
from core.catalogo import contiene_activo, invalidar_cache, obtener_nombre_compania_existe
from core.comandas.repository import total_comandas
from core.config import LOGS_DIR

router = APIRouter(prefix="/api")


def _get_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("session")
    return get_user_from_token(token) if token else None


def _require_auth(request: Request):
    user = _get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user


def _require_admin(request: Request):
    user = _require_auth(request)
    if user.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    return user


# ── Dashboard Stats ────────────────────────────────────────────
@router.get("/dashboard/stats")
def dashboard_stats(request: Request):
    _require_auth(request)

    # Altas y bajas se cuentan sobre la tabla `personal` (una fila por persona),
    # NO sobre `solicitudes`: contar solicitudes mezcla dos unidades distintas
    # y subestima ~19x. Un count=exact con Range 0-0 da el total real en el
    # header Content-Range sin transferir filas, asi que no sufre el cap de
    # 1000 filas por response de PostgREST.
    #
    # estos conteos cuadran con el grafico "Altas vs Bajas", que suma
    # solicitudes.n_personas / solicitudes.n_bajas: ambas vias dan 5059 altas
    # y 3493 bajas.
    return {
        "total_solicitudes": _count_rows("solicitudes"),
        # Un "movimiento" es una fila de `personal`: un alta o una baja. No es
        # un padrón de personas: el mismo RFC aparece una vez por cada solicitud
        # en que sube o baja, asi que este total es >= que el de RFC distintos.
        # Es la suma de las dos tarjetas vecinas (ver `hint` en el frontend).
        "total_movimientos": _count_rows("personal"),
        "altas_generadas": _count_rows("personal", {"tipo": "eq.sube"}),
        "bajas_procesadas": _count_rows("personal", {"tipo": "eq.baja"}),
        "total_companias": _count_rows("companias"),
        # Comandas de alimentos de los dos barcos, de todos los usuarios. Es la
        # unica cifra de esta tarjeta que viene del modulo de comandas, asi que
        # se pide ahi y no con un `_count_rows` aqui: el modulo de comandas es
        # el que sabe de esa tabla y de sus reglas. Global, como las demas.
        "total_comandas": total_comandas(),
    }


# ── Solicitudes list ───────────────────────────────────────────
def _agregar_ultimos_dias(dias: int, barco: str = "") -> tuple:
    """Agrega n_personas/n_bajas por destino (RPX/CPZ) por día en una ventana de `dias` días."""
    dias = max(1, min(dias, 365))
    hoy = date.today()
    fechas = [(hoy - timedelta(days=i)).isoformat() for i in range(dias - 1, -1, -1)]
    mapa = {
        d: {
            "rpx": {"altas": 0, "bajas": 0},
            "cpz": {"altas": 0, "bajas": 0},
        }
        for d in fechas
    }
    barcos: set = set()

    try:
        # Filtrar por inicio de ventana en Supabase: menos datos transferidos,
        # evita el cap de 1000 filas por response de PostgREST.
        rows = _get("solicitudes",
                    select="fecha_llegada,transporte,n_personas,n_bajas,destinohosp",
                    filters={"fecha_llegada": f"gte.{fechas[0]}"})
        for r in rows:
            f = (r.get("fecha_llegada") or "")[:10]
            if f not in mapa:
                continue
            dest = (r.get("destinohosp") or "").strip().upper()
            if dest not in ("RPX", "CPZ"):
                continue
            transporte = r.get("transporte") or ""
            if transporte:
                barcos.add(transporte)
            if barco and transporte != barco:
                continue
            try:
                altas = int(r.get("n_personas") or 0)
            except (TypeError, ValueError):
                altas = 0
            try:
                bajas = int(r.get("n_bajas") or 0)
            except (TypeError, ValueError):
                bajas = 0
            mapa[f][dest.lower()]["altas"] += altas
            mapa[f][dest.lower()]["bajas"] += bajas
    except Exception:
        pass

    return fechas, sorted(barcos), mapa


@router.get("/dashboard/programacion-dias")
def programacion_dias(request: Request, dias: int = 14):
    """Personas programadas (altas) por destino RPX/CPZ en los últimos `dias` días."""
    _require_auth(request)

    fechas, _, mapa = _agregar_ultimos_dias(dias)
    return {
        "dias": fechas,
        "rpx": [mapa[d]["rpx"]["altas"] for d in fechas],
        "cpz": [mapa[d]["cpz"]["altas"] for d in fechas],
    }


@router.get("/dashboard/programacion-area")
def programacion_area(request: Request, dias: int = 14, barco: str = ""):
    """Comportamiento de altas vs bajas por destino en los últimos `dias` días, con filtro de barco."""
    _require_auth(request)

    fechas, barcos, mapa = _agregar_ultimos_dias(dias, barco)
    return {
        "dias": fechas,
        "barcos": barcos,
        "rpx": {
            "altas": [mapa[d]["rpx"]["altas"] for d in fechas],
            "bajas": [mapa[d]["rpx"]["bajas"] for d in fechas],
        },
        "cpz": {
            "altas": [mapa[d]["cpz"]["altas"] for d in fechas],
            "bajas": [mapa[d]["cpz"]["bajas"] for d in fechas],
        },
    }


@router.get("/solicitudes")
def solicitudes_list(request: Request, page: int = 1, search: str = ""):
    _require_auth(request)
    
    limit = 10
    solicitudes, total = listar_solicitudes_xlsx(page=page, limit=limit, search=search)
    total_pages = math.ceil(total / limit)
    
    return {
        "solicitudes": [
            {
                "id": s.get("id", 0),
                "folio": s.get("nombre", s.get("folio", "")),
                "tipo": s.get("tipo", "solicitud"),
                "estatus": "completado" if s.get("procesado") else "pendiente",
                "personal_count": s.get("n", s.get("n_personas", 0)),
                "bajas_count": s.get("n_bajas", 0),
                "compania": s.get("compania", ""),
                "destino": s.get("destino", s.get("destinohosp", "")),
                "created_at": s.get("fecha", s.get("fecha_mod", s.get("created_at", ""))),
            }
            for s in solicitudes
        ],
        "total": total,
        "page": page,
        "total_pages": total_pages,
    }


# ── Compañías ──────────────────────────────────────────────────
#
# Los seis endpoints exigen sesion. Antes no la exigian: con la URL a mano
# cualquiera podia POSTear o DELETEear en companias y activos sin estar
# autenticado, y un borrado desde una pestana sin sesion dejaba el catalogo sin
# la razon social que el procesador usa para el alias de la celda E8.
#
# Cada alta o baja invalida la cache del catalogo (core/catalogo.py). Sin esto,
# agregar una compania tardaba hasta 5 minutos en verse en los Excel generados,
# que es justo la confusion que reporto el usuario al empezar: la compania estaba
# en la tabla pero el alias no aparecia.
class CompaniaCreate(BaseModel):
    razon_social: str
    nombre_corto: str


@router.get("/companias")
async def companias_list(request: Request):
    _require_auth(request)
    data = leer_companias_supabase()
    return [
        {
            "id": str(c.get("id", "")),
            "razon_social": c.get("razon_social", ""),
            "nombre_corto": c.get("nombre_corto", ""),
        }
        for c in data
    ]


@router.post("/companias")
async def companias_create(request: Request, req: CompaniaCreate):
    _require_auth(request)

    razon = (req.razon_social or "").strip()
    if not razon:
        raise HTTPException(status_code=400, detail="La razón social está vacía")

    # `_post` inserta sin comprobar duplicados. Sin esto, dar dos veces en Guardar
    # deja dos filas y `obtener_nombre_compania` agarra la primera que encuentra,
    # que no necesariamente es la que acaba de escribir el usuario.
    if obtener_nombre_compania_existe(razon):
        raise HTTPException(status_code=409, detail=f"'{razon}' ya está en la lista")

    agregar_compania_supabase(razon, (req.nombre_corto or "").strip())
    invalidar_cache(companias=True, activos=False)
    return {"ok": True}


@router.delete("/companias/{razon_social}")
async def companias_delete(request: Request, razon_social: str):
    _require_auth(request)
    eliminar_compania_supabase(razon_social)
    invalidar_cache(companias=True, activos=False)
    return {"ok": True}


# ── Activos ────────────────────────────────────────────────────
class ActivoCreate(BaseModel):
    nombre: str


@router.get("/activos")
async def activos_list(request: Request):
    _require_auth(request)
    data = leer_activos_supabase()
    return [{"id": "", "nombre": a} for a in data]


@router.post("/activos")
async def activos_create(request: Request, req: ActivoCreate):
    _require_auth(request)

    nombre = (req.nombre or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre del activo está vacío")
    if contiene_activo(nombre):
        raise HTTPException(status_code=409, detail=f"'{nombre}' ya está en la lista")

    agregar_activo_supabase(nombre)
    invalidar_cache(companias=False, activos=True)
    return {"ok": True}


@router.delete("/activos/{nombre}")
async def activos_delete(request: Request, nombre: str):
    _require_auth(request)
    eliminar_activo_supabase(nombre)
    invalidar_cache(companias=False, activos=True)
    return {"ok": True}


# ── Bajas ──────────────────────────────────────────────────────
@router.get("/bajas")
async def bajas_list():
    data = listar_bajas_db()
    return data


# ── Logs ───────────────────────────────────────────────────────
@router.get("/logs")
async def logs_get():
    fecha = datetime.now().strftime("%d/%m/%Y")
    log_file = LOGS_DIR / f"precarga_{datetime.now().strftime('%Y%m%d')}.log"
    contenido = log_file.read_text(encoding="utf-8") if log_file.exists() else "Sin logs disponibles."
    return {"fecha": fecha, "contenido": contenido}


# ── Admin: Usuarios ────────────────────────────────────────────
@router.get("/admin/usuarios")
async def admin_usuarios_list(request: Request):
    _require_admin(request)
    usuarios = listar_usuarios()
    return [
        {
            "id": str(u.get("id", "")),
            "nombre": u.get("username", ""),
            "email": u.get("email", ""),
            "admin": u.get("rol") == "admin",
            "verificado": u.get("email_verificado", u.get("verificado", False)),
            "created_at": u.get("creado", ""),
        }
        for u in usuarios
    ]


@router.patch("/admin/usuarios/{uid}")
async def admin_usuarios_update(uid: str, request: Request):
    _require_admin(request)
    body = await request.json()
    update_data = {}
    if "admin" in body:
        update_data["rol"] = "admin" if body["admin"] else "usuario"
    if "verificado" in body:
        # La columna en la BD se llama email_verificado; enviar
        # "verificado" devolvia 400 de PostgREST.
        update_data["email_verificado"] = body["verificado"]
    if update_data:
        from core.supabase_db import _patch
        _patch("usuarios", update_data, {"id": f"eq.{uid}"})
    return {"ok": True}


# ── Planes (Stripe) ────────────────────────────────────────────
@router.get("/planes")
async def planes_list():
    from core.stripe import STRIPE_PRICE, STRIPE_DAYS, STRIPE_CURRENCY
    # Single plan configured via environment variables
    precio_mxn = STRIPE_PRICE / 100  # Convert from cents
    return [
        {
            "id": "plan_default",
            "nombre": f"Suscripción {STRIPE_DAYS} días",
            "precio": precio_mxn,
            "descargas": 999999,  # Unlimited downloads with subscription
        }
    ]
