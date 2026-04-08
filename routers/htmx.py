"""routers/htmx.py — Endpoints HTMX que devuelven fragmentos HTML parciales"""
from datetime import datetime
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from templates_cfg import templates

from core import (
    leer_companias, guardar_companias,
    leer_activos, guardar_activos,
    listar_solicitudes_xlsx,
)

router = APIRouter(prefix="/htmx")


# ── Lista de solicitudes (recargable) ─────────────────────────
@router.get("/solicitudes", response_class=HTMLResponse)
async def solicitudes_parcial(request: Request):
    # listar_solicitudes_xlsx() ya devuelve dicts desde la BD
    solicitudes = listar_solicitudes_xlsx()
    return templates.TemplateResponse(request, "partials/solicitudes.html",
                                      {"solicitudes": solicitudes})


# ── Compañías: agregar ────────────────────────────────────────
@router.post("/companias/agregar", response_class=HTMLResponse)
async def companias_agregar(request: Request,
                             razon_social: str = Form(...),
                             nombre_corto: str = Form(...)):
    companias = leer_companias()
    razon_social = razon_social.strip()
    nombre_corto = nombre_corto.strip()

    # Verificar duplicado
    existe = any(c["razon_social"].strip().lower() == razon_social.lower()
                 for c in companias)
    if not existe:
        companias.append({"razon_social": razon_social, "nombre_corto": nombre_corto})
        guardar_companias(companias)

    return templates.TemplateResponse(request, "partials/tabla_companias.html", {"companias": leer_companias()})


# ── Compañías: eliminar ───────────────────────────────────────
@router.post("/companias/eliminar", response_class=HTMLResponse)
async def companias_eliminar(request: Request, razon_social: str = Form(...)):
    companias = [c for c in leer_companias()
                 if c["razon_social"].strip() != razon_social.strip()]
    guardar_companias(companias)
    return templates.TemplateResponse(request, "partials/tabla_companias.html", {"companias": leer_companias()})


# ── Activos: agregar ──────────────────────────────────────────
@router.post("/activos/agregar", response_class=HTMLResponse)
async def activos_agregar(request: Request, activo: str = Form(...)):
    activos = leer_activos()
    nombre  = activo.strip()
    if nombre and not any(a.lower() == nombre.lower() for a in activos):
        activos.append(nombre)
        guardar_activos(activos)
    return templates.TemplateResponse(request, "partials/lista_activos.html", {"activos": leer_activos()})


# ── Activos: eliminar ─────────────────────────────────────────
@router.post("/activos/eliminar", response_class=HTMLResponse)
async def activos_eliminar(request: Request, activo: str = Form(...)):
    activos = [a for a in leer_activos() if a.strip() != activo.strip()]
    guardar_activos(activos)
    return templates.TemplateResponse(request, "partials/lista_activos.html", {"activos": leer_activos()})
