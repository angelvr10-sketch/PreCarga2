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

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from routers import pages, api, htmx

app = FastAPI(title="Precarga SHAT", version="0.3-web", docs_url=None)

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
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(htmx.router)
