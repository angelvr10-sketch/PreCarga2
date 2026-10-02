"""routers/auth.py — Logout de emergencia (sin template)

La autenticacion de la SPA vive en routers/api_auth.py con prefijo
/api/auth (login, register, verify, logout, me), que es lo que consume
el frontend React.

Este modulo conserva un unico GET /logout para poder cerrar sesion
desde el navegador (bookmark o sesion trabada) sin depender del
cliente. No renderiza nada: siempre redirige.
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.auth import logout

router = APIRouter()


@router.get("/logout", include_in_schema=False)
async def logout_route(request: Request):
    token = request.cookies.get("session")
    if token:
        logout(token)
    # Mismo destino que el boton "Cerrar Sesion" de la SPA (use-logout.ts).
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("session")
    return response
