"""routers/pages.py — Rutas de páginas HTML completas"""
import csv
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core import (
    leer_companias, leer_activos,
    listar_solicitudes_xlsx, listar_archivos_baja,
    leer_meta_xlsx, leer_meta_baja,
)
from core.config import SOL_DIR, LOGS_DIR

router     = APIRouter()
templates  = Jinja2Templates(directory="templates")


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
    sol = list(SOL_DIR.glob("*.xlsx")) if SOL_DIR.exists() else []
    baj = list(SOL_DIR.glob("*-B.csv")) if SOL_DIR.exists() else []
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
    return templates.TemplateResponse(request, "dashboard.html", {"page": "dashboard",
        "stats": stats, "solicitudes": ultimas,})


# ── Procesar PDFs ────────────────────────────────────────────
@router.get("/procesar", response_class=HTMLResponse)
async def procesar(request: Request):
    return templates.TemplateResponse(request, "procesar.html", {"page": "procesar",})


# ── Altas ─────────────────────────────────────────────────────
@router.get("/altas", response_class=HTMLResponse)
async def altas(request: Request):
    archivos = listar_solicitudes_xlsx()
    return templates.TemplateResponse(request, "altas.html", {"page": "altas",
        "solicitudes": _sol_rows(archivos),})


# ── Bajas ─────────────────────────────────────────────────────
@router.get("/bajas", response_class=HTMLResponse)
async def bajas(request: Request):
    archivos = listar_archivos_baja()
    return templates.TemplateResponse(request, "bajas.html", {"page": "bajas",
        "bajas": _baja_rows(archivos),})


# ── Compañías ─────────────────────────────────────────────────
@router.get("/companias", response_class=HTMLResponse)
async def companias(request: Request):
    return templates.TemplateResponse(request, "companias.html", {"page": "companias",
        "companias": leer_companias(),})


# ── Activos ───────────────────────────────────────────────────
@router.get("/activos", response_class=HTMLResponse)
async def activos(request: Request):
    return templates.TemplateResponse(request, "activos.html", {"page": "activos",
        "activos": leer_activos(),})


# ── Logs ──────────────────────────────────────────────────────
@router.get("/logs", response_class=HTMLResponse)
async def logs(request: Request):
    fecha    = datetime.now().strftime("%d/%m/%Y")
    log_file = LOGS_DIR / f"precarga_{datetime.now().strftime('%Y%m%d')}.log"
    contenido = log_file.read_text(encoding="utf-8") if log_file.exists() else "Sin logs disponibles."
    return templates.TemplateResponse(request, "logs.html", {"page": "logs",
        "fecha": fecha, "contenido": contenido,})
