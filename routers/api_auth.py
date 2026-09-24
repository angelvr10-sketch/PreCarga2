"""routers/api_auth.py — Endpoints JSON de autenticación para el frontend SPA"""
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from core.auth import (
    login as auth_login,
    logout as auth_logout,
    get_user_from_token,
    get_current_user,
    registrar_enviar_codigo,
    verificar_codigo_y_crear_cuenta,
    listar_usuarios,
    _ip_from_request,
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


def _serialize_user(user: dict) -> dict:
    """Convierte un usuario de BD a formato JSON para el frontend."""
    return {
        "id": str(user.get("id", "")),
        "nombre": user.get("username", user.get("nombre", "")),
        "email": user.get("email", ""),
        "admin": user.get("rol") == "admin",
        "verificado": user.get("verificado", False),
        "created_at": user.get("creado", ""),
    }


# ── GET /api/auth/me ───────────────────────────────────────────
@router.get("/me")
async def me(request: Request):
    token = request.cookies.get("session")
    user = get_user_from_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    return {"user": _serialize_user(user)}


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


# ── POST /api/auth/logout ───────────────────────────────────────
@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get("session")
    if token:
        auth_logout(token)
    response = JSONResponse({"ok": True})
    response.delete_cookie("session")
    return response
