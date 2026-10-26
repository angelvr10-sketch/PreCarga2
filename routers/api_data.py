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
    _get, _count_rows, _patch, _delete,
)
from core.db import listar_bajas_db, listar_solicitudes_db
from core.auth import (
    get_user_from_token,
    listar_usuarios,
    registrar as auth_registrar,
    eliminar_usuario,
    agregar_dias,
    _hash,
)
from core.catalogo import contiene_activo, invalidar_cache, obtener_nombre_compania_existe
from core.comandas.repository import total_comandas
from core.config import LOGS_DIR, DIAS_FUTURO

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
    """Agrega n_personas/n_bajas por destino (RPX/CPZ) por día en una ventana de `dias` días.

    La ventana va `DIAS_FUTURO` días más allá de hoy: el eje X no se corta en el
    borde, sino que deja ver los próximos días. El historico NO se recorta — con
    30 días se siguen viendo los mismos 30 y se suman 2 al final. Es el mismo
    recorte que `core/comandas/serie.py::ventana`, y tiene que serlo: las dos
    graficas comparten el selector de periodo, asi que si una redondeara distinto
    la comparación entre ellas sería falsa.
    """
    dias = max(1, min(dias, 365))
    hoy = date.today()
    # Un solo rango: unir dos listasinvariantemente deja un dia repetido o un
    # hueco, que es donde se desalinearia el eje X de las cuatro series.
    fechas = [
        (hoy + timedelta(days=i)).isoformat()
        for i in range(-(dias - 1), DIAS_FUTURO + 1)
    ]
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
ROLES_VALIDOS = ("admin", "usuario", "lector")
MAX_DIAS_SUSCRIPCION = 3650


def _serialize_admin_user(u: dict) -> dict:
    return {
        "id": str(u.get("id", "")),
        "nombre": u.get("username", ""),
        "email": u.get("email") or "",
        "rol": u.get("rol") or "usuario",
        "admin": u.get("rol") == "admin",
        "activo": bool(u.get("activo", True)),
        "verificado": bool(u.get("email_verificado", u.get("verificado", False))),
        "descargas_usadas": u.get("descargas_usadas") or 0,
        "expira": u.get("expira"),
        "created_at": u.get("creado", ""),
    }


def _dias_del_body(body: dict) -> int:
    raw = body.get("dias")
    if raw is None:
        return 0
    try:
        dias = int(raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Los días deben ser un número entero")
    if dias < 0 or dias > MAX_DIAS_SUSCRIPCION:
        raise HTTPException(
            status_code=400,
            detail=f"Los días deben estar entre 0 y {MAX_DIAS_SUSCRIPCION}",
        )
    return dias


@router.get("/admin/usuarios")
async def admin_usuarios_list(request: Request):
    _require_admin(request)
    return [_serialize_admin_user(u) for u in listar_usuarios()]


@router.post("/admin/usuarios")
async def admin_usuarios_create(request: Request):
    _require_admin(request)
    body = await request.json()

    username = str(body.get("nombre") or body.get("username") or "").strip()
    email = str(body.get("email") or "").strip()
    password = str(body.get("password") or "")
    rol = str(body.get("rol") or ("admin" if body.get("admin") else "usuario"))
    dias = _dias_del_body(body)

    if rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail="Rol inválido")

    ok, mensaje = auth_registrar(username, password, dias, rol, email or None)
    if not ok:
        raise HTTPException(status_code=400, detail=mensaje)
    return {"ok": True, "mensaje": mensaje}


@router.patch("/admin/usuarios/{uid}")
async def admin_usuarios_update(uid: str, request: Request):
    actual = _require_admin(request)
    body = await request.json()

    # Un admin no puede quitarse a si mismo el rol ni desactivarse: dejaria
    # la aplicacion sin ningun administrador y no hay forma de deshacerlo
    # desde la interfaz.
    es_uno_mismo = str(actual.get("id")) == str(uid)

    update_data = {}

    if "rol" in body or "admin" in body:
        rol = str(body.get("rol") or "usuario")
        if "rol" not in body:
            rol = "admin" if body.get("admin") else "usuario"
        if rol not in ROLES_VALIDOS:
            raise HTTPException(status_code=400, detail="Rol inválido")
        if es_uno_mismo and rol != "admin":
            raise HTTPException(
                status_code=400,
                detail="No puedes quitarte a ti mismo el rol de administrador",
            )
        update_data["rol"] = rol

    if "activo" in body:
        activo = bool(body["activo"])
        if es_uno_mismo and not activo:
            raise HTTPException(
                status_code=400,
                detail="No puedes desactivar tu propia cuenta",
            )
        update_data["activo"] = activo

    if "verificado" in body:
        # La columna en la BD se llama email_verificado; enviar
        # "verificado" devolvia 400 de PostgREST.
        update_data["email_verificado"] = bool(body["verificado"])

    if body.get("password") is not None:
        password = str(body["password"])
        if len(password) < 6:
            raise HTTPException(
                status_code=400,
                detail="La contraseña debe tener al menos 6 caracteres",
            )
        update_data["password"] = _hash(password)

    dias = _dias_del_body(body)
    if dias:
        agregar_dias(uid, dias)

    if update_data:
        _patch("usuarios", update_data, {"id": f"eq.{uid}"})

    # Restablecer la contrasena de otra persona cierra sus sesiones abiertas:
    # si no, la contrasena nueva no protege nada porque el token anterior
    # sigue siendo valido hasta 24 h. Al cambiar la propia no se toca, para
    # no expulsar al admin de la sesion en la que esta trabajando.
    if "password" in update_data and not es_uno_mismo:
        _delete("sesiones", {"usuario_id": f"eq.{uid}"})

    return {"ok": True}


@router.delete("/admin/usuarios/{uid}")
async def admin_usuarios_delete(uid: str, request: Request):
    actual = _require_admin(request)
    if str(actual.get("id")) == str(uid):
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")

    if not _get("usuarios", filters={"id": f"eq.{uid}"}, select="id"):
        raise HTTPException(status_code=404, detail="El usuario no existe")

    try:
        eliminar_usuario(uid)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo eliminar el usuario: {e}",
        )
    return {"ok": True}


# ── Planes (Stripe) ────────────────────────────────────────────
@router.get("/planes")
async def planes_list():
    from core.stripe import listar_planes
    return listar_planes()
