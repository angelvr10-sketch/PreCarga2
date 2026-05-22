"""routers/pages.py — Rutas de páginas HTML completas"""
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from templates_cfg import templates

from core import (
    leer_companias, leer_activos,
    listar_solicitudes_xlsx, listar_archivos_baja,
    leer_meta_baja,
)
from core.db import listar_bajas_db
from core.config import SOL_DIR, LOGS_DIR
from core.auth import get_current_user, require_login

router = APIRouter()


def _baja_rows(archivos):
    rows = []
    for p in archivos:
        meta = leer_meta_baja(p)
        rows.append({"nombre": p.stem, "compania": meta["compania"], "n": meta["n"]})
    return rows


# ── Landing Page ─────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request, "landing.html", {})


# ── Dashboard ────────────────────────────────────────────────
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    redir = require_login(request)
    if redir:
        return redir
    user = get_current_user(request)
    from core.db import listar_solicitudes_db
    sol_db = listar_solicitudes_db(limit=8)
    baj    = list(SOL_DIR.glob("*-B.csv")) if SOL_DIR.exists() else []
    
    # Corregimos el acceso a stats para evitar el error de tupla
    res_sol = listar_solicitudes_xlsx()
    sol_count = res_sol[1] if isinstance(res_sol, tuple) else len(res_sol)
    
    stats  = {
        "solicitudes": sol_count,
        "bajas":       len(baj),
        "companias":   len(leer_companias()),
        "activos":     len(leer_activos()),
    }
    # Enriquecer con fecha_mod desde disco
    ultimas = []
    for r in sol_db:
        archivo = SOL_DIR / r["archivo"] if r.get("archivo") else None
        fecha_mod = ""
        if archivo and archivo.exists():
            fecha_mod = datetime.fromtimestamp(
                archivo.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
        ultimas.append({**r, "nombre": r["numero"],
                        "n": r["n_personas"], "fecha_mod": fecha_mod})
    return templates.TemplateResponse(request, "dashboard.html", {
        "page": "dashboard", "user": user,
        "stats": stats, "solicitudes": ultimas,
    })


# ── Procesar PDFs ────────────────────────────────────────────
@router.get("/procesar", response_class=HTMLResponse)
async def procesar(request: Request):
    redir = require_login(request)
    if redir:
        return redir
    return templates.TemplateResponse(request, "procesar.html", {
        "page": "procesar", "user": get_current_user(request),
    })


# ── Altas ─────────────────────────────────────────────────────
@router.get("/altas", response_class=HTMLResponse)
async def altas(request: Request):
    redir = require_login(request)
    if redir:
        return redir
    
    search = request.query_params.get("search", "").strip()
    
    # Desestructuramos la tupla (datos, total) para enviar solo la lista al template
    res = listar_solicitudes_xlsx(search=search)
    solicitudes = res[0] if isinstance(res, tuple) else res
    
    return templates.TemplateResponse(request, "altas.html", {
        "page": "altas", "user": get_current_user(request),
        "solicitudes": solicitudes,
        "search": search,
    })


# ── Bajas ─────────────────────────────────────────────────────
@router.get("/bajas", response_class=HTMLResponse)
async def bajas(request: Request):
    redir = require_login(request)
    if redir:
        return redir
    archivos = listar_archivos_baja()
    return templates.TemplateResponse(request, "bajas.html", {
        "page": "bajas", "user": get_current_user(request),
        "bajas": _baja_rows(archivos),
    })


# ── Compañías ─────────────────────────────────────────────────
@router.get("/companias", response_class=HTMLResponse)
async def companias(request: Request):
    redir = require_login(request)
    if redir:
        return redir
    return templates.TemplateResponse(request, "companias.html", {
        "page": "companias", "user": get_current_user(request),
        "companias": leer_companias(),
    })


# ── Activos ───────────────────────────────────────────────────
@router.get("/activos", response_class=HTMLResponse)
async def activos(request: Request):
    redir = require_login(request)
    if redir:
        return redir
    return templates.TemplateResponse(request, "activos.html", {
        "page": "activos", "user": get_current_user(request),
        "activos": leer_activos(),
    })


# ── Logs ──────────────────────────────────────────────────────
@router.get("/logs", response_class=HTMLResponse)
async def logs(request: Request):
    redir = require_login(request)
    if redir:
        return redir
    fecha     = datetime.now().strftime("%d/%m/%Y")
    log_file  = LOGS_DIR / f"precarga_{datetime.now().strftime('%Y%m%d')}.log"
    contenido = log_file.read_text(encoding="utf-8") if log_file.exists() else "Sin logs disponibles."
    return templates.TemplateResponse(request, "logs.html", {
        "page": "logs", "user": get_current_user(request),
        "fecha": fecha, "contenido": contenido,
    })
