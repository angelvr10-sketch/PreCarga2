"""routers/pages.py — Rutas de páginas HTML completas"""
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from templates_cfg import templates

from core import (
    leer_companias, leer_activos,
    listar_solicitudes_xlsx, listar_archivos_baja,
    leer_meta_xlsx, leer_meta_baja,
)
from core.config import SOL_DIR, LOGS_DIR
from core.auth import get_current_user, require_login

router    = APIRouter()


def _sol_rows(archivos):
    rows = []
    for p in archivos:
        meta = leer_meta_xlsx(p)
        rows.append({
            "nombre":    p.stem,
            "compania":  meta["compania"],
            "n":         meta["n"],
            "fecha":     meta["fecha"],
            "fecha_mod": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
        })
    return rows


def _baja_rows(archivos):
    rows = []
    for p in archivos:
        meta = leer_meta_baja(p)
        rows.append({"nombre": p.stem, "compania": meta["compania"], "n": meta["n"]})
    return rows


# ── Dashboard ────────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    redir = require_login(request)
    if redir:
        return redir
    user = get_current_user(request)
    sol  = list(SOL_DIR.glob("*.xlsx")) if SOL_DIR.exists() else []
    baj  = list(SOL_DIR.glob("*-B.csv")) if SOL_DIR.exists() else []
    stats = {
        "solicitudes": len([p for p in sol if not p.stem.endswith("-B")]),
        "bajas":       len(baj),
        "companias":   len(leer_companias()),
        "activos":     len(leer_activos()),
    }
    ultimas = _sol_rows(
        sorted([p for p in sol if not p.stem.endswith("-B")],
               key=lambda p: p.stat().st_mtime, reverse=True)[:8]
    )
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
    archivos = listar_solicitudes_xlsx()
    return templates.TemplateResponse(request, "altas.html", {
        "page": "altas", "user": get_current_user(request),
        "solicitudes": _sol_rows(archivos),
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
