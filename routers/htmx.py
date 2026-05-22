"""routers/htmx.py — Endpoints HTMX que devuelven fragmentos HTML parciales"""
import math
from datetime import datetime
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from templates_cfg import templates

from core.supabase_db import (
    leer_companias_supabase, agregar_compania_supabase, eliminar_compania_supabase,
    leer_activos_supabase, agregar_activo_supabase, eliminar_activo_supabase
)
from core import listar_solicitudes_xlsx


router = APIRouter(prefix="/htmx")


# ── Lista de solicitudes (recargable) ─────────────────────────
@router.get("/solicitudes", response_class=HTMLResponse)
async def solicitudes_parcial(request: Request, page: int = 1, search: str = ""):
    limit = 10
    # listar_solicitudes_xlsx ahora devuelve (datos, total)
    solicitudes, total = listar_solicitudes_xlsx(page=page, limit=limit, search=search)
    
    total_pages = math.ceil(total / limit)
    
    return templates.TemplateResponse(request, "partials/solicitudes.html", {
        "solicitudes": solicitudes,
        "page": page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "search": search
    })


# ── Compañías: agregar ────────────────────────────────────────
@router.post("/companias/agregar", response_class=HTMLResponse)
async def companias_agregar(request: Request,
                             razon_social: str = Form(...),
                             nombre_corto: str = Form(...)):
    razon_social = razon_social.strip()
    nombre_corto = nombre_corto.strip()

    # Verificar duplicado en Supabase
    companias = leer_companias_supabase()
    existe = any(c["razon_social"].strip().lower() == razon_social.lower()
                 for c in companias)
    if not existe:
        agregar_compania_supabase(razon_social, nombre_corto)

    return templates.TemplateResponse(request, "partials/tabla_companias.html", {"companias": leer_companias_supabase()})


# ── Compañías: eliminar ───────────────────────────────────────
@router.post("/companias/eliminar", response_class=HTMLResponse)
async def companias_eliminar(request: Request, razon_social: str = Form(...)):
    eliminar_compania_supabase(razon_social.strip())
    return templates.TemplateResponse(request, "partials/tabla_companias.html", {"companias": leer_companias_supabase()})


# ── Activos: agregar ──────────────────────────────────────────
@router.post("/activos/agregar", response_class=HTMLResponse)
async def activos_agregar(request: Request, activo: str = Form(...)):
    nombre = activo.strip()
    activos = leer_activos_supabase()
    if nombre and not any(a.lower() == nombre.lower() for a in activos):
        agregar_activo_supabase(nombre)
    return templates.TemplateResponse(request, "partials/lista_activos.html", {"activos": leer_activos_supabase()})


# ── Activos: eliminar ─────────────────────────────────────────
@router.post("/activos/eliminar", response_class=HTMLResponse)
async def activos_eliminar(request: Request, nombre: str = Form(...)):
    eliminar_activo_supabase(nombre.strip())
    return templates.TemplateResponse(request, "partials/lista_activos.html", {"activos": leer_activos_supabase()})
