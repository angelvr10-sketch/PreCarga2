"""routers/auth.py — Rutas de autenticación y administración de usuarios

Flujo de registro con verificación por email:
1. GET /registro -> Muestra formulario con email
2. POST /registro/iniciar -> Valida datos, envía código, redirige a /verificar
3. GET /verificar -> Muestra formulario de código
4. POST /verificar -> Verifica código y crea cuenta
5. POST /registro/reenviar -> Reenvía código
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from templates_cfg import templates

from core.auth import (
    login, logout, registrar,
    listar_usuarios, eliminar_usuario,
    agregar_dias, toggle_activo,
    get_current_user, require_admin,
    dias_restantes,
    registrar_enviar_codigo, verificar_codigo_y_crear_cuenta,
    reenviar_codigo, _ip_from_request
)

router = APIRouter()


# ── Login ─────────────────────────────────────────────────────
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, expired: int = 0, error: int = 0, registered: int = 0):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {
        "expired": expired, "error": error, "registered": registered
    })


@router.post("/login")
async def login_post(request: Request,
                     username: str = Form(...),
                     password: str = Form(...)):
    token = login(username, password)
    if not token:
        # Verificar si existe el usuario para dar mensaje apropiado
        return RedirectResponse("/login?error=1", status_code=303)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("session", token, httponly=True,
                        max_age=86400, samesite="lax")
    return response


# ── Logout ────────────────────────────────────────────────────
@router.get("/logout")
async def logout_route(request: Request):
    token = request.cookies.get("session")
    if token:
        logout(token)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session")
    return response


# ── Registro con verificación por email ───────────────────────
@router.get("/registro", response_class=HTMLResponse)
async def registro_page(request: Request, error: str = None, info: str = None):
    return templates.TemplateResponse(request, "registro.html", {"error": error, "info": info})


@router.post("/registro/iniciar")
async def registro_iniciar(request: Request,
                           email: str = Form(...),
                           username: str = Form(...),
                           password: str = Form(...),
                           password2: str = Form(...)):
    if password != password2:
        return templates.TemplateResponse(request, "registro.html",
                                          {"error": "Las contraseñas no coinciden"})

    ip = _ip_from_request(request)
    ok, msg = registrar_enviar_codigo(email, username, password, ip)

    if not ok:
        return templates.TemplateResponse(request, "registro.html", {"error": msg})

    # Redirigir a verificación con email en query param
    return RedirectResponse(f"/verificar?email={email}", status_code=303)


@router.get("/verificar", response_class=HTMLResponse)
async def verificar_page(request: Request, email: str = "", error: str = None, info: str = None):
    return templates.TemplateResponse(request, "verificar.html", {
        "email": email,
        "error": error,
        "info": info
    })


@router.post("/verificar")
async def verificar_post(request: Request,
                         email: str = Form(...),
                         codigo: str = Form(...)):
    ok, msg = verificar_codigo_y_crear_cuenta(email, codigo)

    if not ok:
        return RedirectResponse(
            f"/verificar?email={email}&error={msg}",
            status_code=303
        )

    # Éxito - redirigir a login con mensaje
    return RedirectResponse("/login?registered=1", status_code=303)


@router.post("/registro/reenviar")
async def registro_reenviar(request: Request, email: str = Form(...)):
    ok, msg = reenviar_codigo(email)
    if not ok:
        return RedirectResponse(f"/verificar?email={email}&error={msg}", status_code=303)
    return RedirectResponse(f"/verificar?email={email}&info={msg}", status_code=303)


# ── Admin: gestión de usuarios ────────────────────────────────
@router.get("/admin/usuarios", response_class=HTMLResponse)
async def admin_usuarios(request: Request):
    redir = require_admin(request)
    if redir:
        return redir
    return templates.TemplateResponse(request, "admin_usuarios.html", {
        "usuarios": listar_usuarios(),
        "user": get_current_user(request),
    })


@router.post("/admin/usuarios/crear")
async def admin_crear(request: Request,
                      username: str = Form(...),
                      password: str = Form(...),
                      dias:     int = Form(30),
                      rol:      str = Form("usuario")):
    redir = require_admin(request)
    if redir:
        return redir
    registrar(username, password, dias=dias, rol=rol)
    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/admin/usuarios/eliminar")
async def admin_eliminar(request: Request, uid: int = Form(...)):
    redir = require_admin(request)
    if redir:
        return redir
    eliminar_usuario(uid)
    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/admin/usuarios/dias")
async def admin_dias(request: Request,
                     uid:  int = Form(...),
                     dias: int = Form(...)):
    redir = require_admin(request)
    if redir:
        return redir
    agregar_dias(uid, dias)
    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/admin/usuarios/toggle")
async def admin_toggle(request: Request, uid: int = Form(...)):
    redir = require_admin(request)
    if redir:
        return redir
    toggle_activo(uid)
    return RedirectResponse("/admin/usuarios", status_code=303)
