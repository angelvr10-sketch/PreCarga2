"""routers/api_auth.py — Endpoints JSON de autenticación para el frontend SPA"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from core.auth import (
    login as auth_login,
    logout as auth_logout,
    cambiar_password,
    solicitar_recuperacion,
    restablecer_password,
    reenviar_codigo,
    get_user_from_token,
    get_current_user,
    registrar_enviar_codigo,
    verificar_codigo_y_crear_cuenta,
    listar_usuarios,
    _ip_from_request,
    _verify_password,
    EMAIL_REGEX,
    MAX_DESCARGAS_GRATIS,
    suscripcion_vigente,
    dias_restantes,
)
from core.supabase_db import _get, _patch

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    nombre: str
    email: str
    password: str


class VerifyRequest(BaseModel):
    email: str
    codigo: str


class ChangePasswordRequest(BaseModel):
    actual: str
    nueva: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResendCodeRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    codigo: str
    nueva: str


class ProfileUpdateRequest(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    actual: Optional[str] = None


def _serialize_user(user: dict) -> dict:
    """Convierte un usuario de BD a formato JSON para el frontend.

    `rol` va aparte de `admin` a proposito. Con solo el booleano `admin` el
    frontend no puede distinguir un `usuario` normal de un `lector`, y terminaba
    tratando a todo el mundo que no fuera admin como lector. El modulo de
    comandas necesita los tres: `admin` y `usuario` pueden generar todos los
    reportes, `lector` solo el estadistico.

    Es un campo ADITIVO: el resto de la app lee `admin` y sigue igual.
    """
    try:
        usadas = int(user.get("descargas_usadas") or 0)
    except (TypeError, ValueError):
        usadas = 0

    return {
        "id": str(user.get("id", "")),
        "nombre": user.get("username", user.get("nombre", "")),
        "email": user.get("email", ""),
        "admin": user.get("rol") == "admin",
        "rol": user.get("rol", ""),
        "verificado": user.get("email_verificado", user.get("verificado", False)),
        "created_at": user.get("creado", ""),
        # Datos para "Mi cuenta": suscripcion y descargas gratuitas.
        "expira": user.get("expira"),
        "suscripcion_vigente": suscripcion_vigente(user),
        "dias_restantes": dias_restantes(user),
        "descargas_usadas": usadas,
        "descargas_gratis_total": MAX_DESCARGAS_GRATIS,
        "descargas_gratis_restantes": max(0, MAX_DESCARGAS_GRATIS - usadas),
    }


# ── GET /api/auth/me ───────────────────────────────────────────
@router.get("/me")
async def me(request: Request):
    token = request.cookies.get("session")
    user = get_user_from_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    return {"user": _serialize_user(user)}


# ── PATCH /api/auth/profile ─────────────────────────────────────
@router.patch("/profile")
async def update_profile(req: ProfileUpdateRequest, request: Request):
    """Actualiza el nombre de usuario y/o el correo de la cuenta.

    Cambiar el correo exige la contraseña actual: la sesión sola no basta.
    Sin esa comprobación, alguien con una cookie robada podría mover la cuenta
    a un correo propio y luego usar "olvidé mi contraseña" para tomarla.
    """
    token = request.cookies.get("session")
    user = get_user_from_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")

    updates: dict = {}
    nombre = req.nombre.strip() if req.nombre is not None else None
    email_norm = req.email.strip().lower() if req.email is not None else None

    if nombre is not None and nombre != user.get("username"):
        if len(nombre) < 3:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "mensaje": "El nombre debe tener al menos 3 caracteres"},
            )
        if len(nombre) > 120:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "mensaje": "El nombre no puede superar 120 caracteres"},
            )
        if _get("usuarios", filters={"username": f"eq.{nombre}"}, select="id", limit=1):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "mensaje": "Ese nombre de usuario ya existe"},
            )
        updates["username"] = nombre

    if email_norm is not None and email_norm != (user.get("email") or "").strip().lower():
        if not EMAIL_REGEX.match(email_norm):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "mensaje": "El correo no tiene un formato válido"},
            )
        if _get("usuarios", filters={"email": f"eq.{email_norm}"}, select="id", limit=1):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "mensaje": "Ese correo ya está registrado"},
            )

        filas = _get("usuarios", filters={"id": f"eq.{user['id']}"},
                     select="password", limit=1)
        if not filas or not _verify_password(req.actual or "", filas[0].get("password", "")):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "mensaje": "La contraseña actual no es correcta"},
            )

        updates["email"] = email_norm
        # El correo nuevo no está verificado todavía. Se muestra el aviso en
        # "Mi cuenta"; la cuenta sigue funcionando con normalidad.
        updates["email_verificado"] = False

    if not updates:
        return {"ok": True, "mensaje": "No hay cambios", "user": _serialize_user(user)}

    _patch("usuarios", updates, {"id": f"eq.{user['id']}"})
    actualizado = get_user_from_token(token) or user
    return {"ok": True, "user": _serialize_user(actualizado)}


# ── POST /api/auth/login ────────────────────────────────────────
@router.post("/login")
async def login(req: LoginRequest):
    token = auth_login(req.email, req.password)
    if not token:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "mensaje": "Credenciales inválidas"},
        )
    # Obtener usuario para devolverlo
    user = get_user_from_token(token)
    response = JSONResponse({
        "ok": True,
        "user": _serialize_user(user) if user else None,
    })
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax",
    )
    return response


# ── POST /api/auth/forgot-password ──────────────────────────────
@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, request: Request):
    """Solicita un código de recuperación. La respuesta no revela si el
    correo existe: el mensaje es el mismo en todos los casos."""
    ip = _ip_from_request(request)
    ok, mensaje = solicitar_recuperacion(req.email, ip)
    return JSONResponse(
        status_code=200 if ok else 400,
        content={"ok": ok, "mensaje": mensaje},
    )


# ── POST /api/auth/reset-password ───────────────────────────────
@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, request: Request):
    ip = _ip_from_request(request)
    ok, mensaje = restablecer_password(req.email, req.codigo, req.nueva, ip)
    return JSONResponse(
        status_code=200 if ok else 400,
        content={"ok": ok, "mensaje": mensaje},
    )


# ── POST /api/auth/change-password ──────────────────────────────
@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, request: Request):
    token = request.cookies.get("session")
    user = get_user_from_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")

    ok, resultado = cambiar_password(user["id"], req.actual, req.nueva)
    if not ok:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "mensaje": resultado},
        )

    # El cambio cierra todas las sesiones y emite un token nuevo: se deja
    # instalado en la cookie para que la sesion actual no se caiga.
    response = JSONResponse({"ok": True, "mensaje": "Contraseña actualizada"})
    response.set_cookie(
        key="session",
        value=resultado,
        httponly=True,
        max_age=86400,
        samesite="lax",
    )
    return response


# ── POST /api/auth/register ─────────────────────────────────────
@router.post("/register")
async def register(req: RegisterRequest, request: Request):
    ip = _ip_from_request(request)
    ok, msg = registrar_enviar_codigo(req.email, req.nombre, req.password, ip)
    if not ok:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "mensaje": msg},
        )
    return {"ok": True, "mensaje": "Código de verificación enviado"}


# ── POST /api/auth/verify ───────────────────────────────────────
@router.post("/verify")
async def verify(req: VerifyRequest):
    ok, msg = verificar_codigo_y_crear_cuenta(req.email, req.codigo)
    if not ok:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "mensaje": msg},
        )
    return {"ok": True, "mensaje": "Cuenta verificada exitosamente"}


# ── POST /api/auth/resend-code ──────────────────────────────────
@router.post("/resend-code")
async def resend_code(req: ResendCodeRequest):
    ok, mensaje = reenviar_codigo(req.email)
    return JSONResponse(
        status_code=200 if ok else 400,
        content={"ok": ok, "mensaje": mensaje},
    )


# ── POST /api/auth/logout ───────────────────────────────────────
@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get("session")
    if token:
        auth_logout(token)
    response = JSONResponse({"ok": True})
    response.delete_cookie("session")
    return response
