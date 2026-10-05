"""
main.py — Precarga
Stack: FastAPI + React (SPA) + API JSON

Frontend: React 19 + Vite, compilado en el Stage 1 del Dockerfile.
El build sale en frontend/dist y se sirve como SPA con fallback a index.html.

Correr (desarrollo):
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Correr (produccion):
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
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

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware

from routers import api, api_auth, api_data
from routers import auth as auth_router
from routers import payments as payments_router
from core.auth import init_db
from core.db import init_solicitudes_db
from core.stripe import init_stripe_payments_db

# Raiz del build de React (Stage 1 del Dockerfile).
DIST_DIR = (_root / "frontend" / "dist").resolve()
INDEX_HTML = DIST_DIR / "index.html"

app = FastAPI(title="Precarga", version="0.4-spa", docs_url=None)

# ── Inicializar BDs al arrancar ───────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    init_solicitudes_db()
    init_stripe_payments_db()

# El cliente HTTP de Supabase es persistente (keep-alive). Sin cerrarlo al
# apagar, cada recarga de `uvicorn --reload` deja el pool de sockets abierto.
@app.on_event("shutdown")
def shutdown():
    from core.supabase_db import cerrar_cliente
    cerrar_cliente()

# ── Middleware ────────────────────────────────────────────────
# El frontend se sirve en el mismo origen que la API, asi que no hace
# falta CORS. Se comprime toda respuesta >1 KB (CSS, JS, JSON y el
# blob de texto de /api/logs, que llega a ~190 KB sin comprimir).
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def cache_static(request: Request, call_next):
    """Starlette no emite Cache-Control en StaticFiles, asi que cada
    /assets/* costo un round-trip condicional (304) en cada carga.
    Los assets llevan hash de contenido: pueden cachearse un año."""
    response = await call_next(request)
    if request.url.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


# ── Build del frontend ────────────────────────────────────────
if DIST_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

# ── Routers ───────────────────────────────────────────────────
# Deben registrarse ANTES del catch-all de la SPA: en FastAPI gana la
# primera coincidencia, asi que las rutas explicitas ganan siempre.
app.include_router(auth_router.router)
app.include_router(payments_router.router)
app.include_router(api.router)
app.include_router(api_auth.router)
app.include_router(api_data.router)


# ── SPA fallback ──────────────────────────────────────────────
# Debe ser la ULTIMA ruta registrada. Sirve los archivos sueltos de la
# raiz del build (favicon, imagenes) y, para cualquier otra ruta de
# navegacion, devuelve index.html para que el router de React resuelva.
@app.get("/{spa_path:path}", include_in_schema=False)
async def spa(request: Request, spa_path: str = ""):
    # Nunca capturar endpoints de API: un 404 con JSON es util,
    # un index.html con status 200 enmascara el error.
    if spa_path.startswith("api/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    # Archivo estatico existente en la raiz del build (favicon, etc).
    # is_relative_to evita path traversal hacia fuera de DIST_DIR.
    if spa_path:
        candidate = (DIST_DIR / spa_path).resolve()
        if candidate.is_relative_to(DIST_DIR) and candidate.is_file():
            return FileResponse(candidate)

    if not INDEX_HTML.is_file():
        return JSONResponse(
            {
                "detail": "Frontend no compilado. Ejecuta 'npm ci && npm run build' en frontend/.",
                "esperado": str(INDEX_HTML),
            },
            status_code=503,
        )

    # index.html nunca se cachea: referencia a los assets con hash.
    return FileResponse(
        INDEX_HTML,
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )
