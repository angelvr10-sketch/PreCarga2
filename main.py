"""
main.py — Precarga SHAT Web
Stack: FastAPI + HTMX + Jinja2

Instalar:
    pip install fastapi uvicorn[standard] jinja2 python-multipart pdfplumber openpyxl

Correr (desarrollo):
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Correr (producción):
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2

Abrir: http://localhost:8000
"""
import os, sys
from pathlib import Path

_root = Path(__file__).resolve().parent

# Cargar variables de entorno desde .env lo primero de todo
# Aseguramos que se carga desde la raíz del proyecto
from dotenv import load_dotenv
load_dotenv(dotenv_path=_root / ".env")

# Garantizar que el directorio del proyecto esté en sys.path
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
os.chdir(_root)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from routers import pages, api, htmx, api_auth, api_data
from routers import auth as auth_router
from routers import payments as payments_router
from core.auth import init_db
from core.db import init_solicitudes_db
from core.stripe import init_stripe_payments_db

app = FastAPI(title="Precarga SHAT", version="0.3-web", docs_url=None)

# ── Inicializar BDs al arrancar ───────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    init_solicitudes_db()
    init_stripe_payments_db()

# ── Middleware ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Archivos estáticos ────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(payments_router.router)
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(api_auth.router)
app.include_router(api_data.router)
app.include_router(htmx.router)
