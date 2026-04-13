"""core/auth.py — Usuarios, sesiones y suscripciones con Supabase"""
import hashlib
import secrets
import os
from datetime import datetime, date, timedelta
from functools import wraps
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from core.supabase_db import (
    _get, _post, _delete, _patch, verificar_conexion, _now,
    HAS_HTTPX, httpx
)


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _fecha_expira(dias: int) -> str:
    return (date.today() + timedelta(days=dias)).strftime("%Y-%m-%d")


def _token() -> str:
    return secrets.token_hex(32)


# ──────────────────────────────────────────────────────────────
#  Inicializacion
# ──────────────────────────────────────────────────────────────

def init_db():
    """Verifica conexion y crea admin por defecto si no existe."""
    if not HAS_HTTPX:
        raise RuntimeError("httpx no esta instalado. pip install httpx")

    # Verificar que Supabase esta configurado
    if not verificar_conexion():
        print("WARNING: No se pudo conectar a Supabase. Verifica SUPABASE_URL y SUPABASE_KEY")
        return

    # Crear admin por defecto si no existe
    existing = _get("usuarios", filters={"username": "eq.admin"})
    if not existing:
        _post("usuarios", {
            "username": "admin",
            "password": _hash("admin123"),
            "rol": "admin",
            "activo": True,
            "creado": _now()
        })
        # Suscripcion de 3650 dias para el admin
        admin_row = _get("usuarios", filters={"username": "eq.admin"})
        if admin_row:
            uid = admin_row[0]["id"]
            _post("suscripciones", {
                "usuario_id": uid,
                "expira": _fecha_expira(3650),
                "creado": _now()
            })
        print("Admin creado por defecto: admin / admin123")
    else:
        print("Conexion a Supabase exitosa")


# ──────────────────────────────────────────────────────────────
#  Autenticacion
# ──────────────────────────────────────────────────────────────

def login(username: str, password: str) -> Optional[str]:
    """
    Verifica credenciales y suscripcion activa.
    Devuelve token de sesion o None.
    """
    # Buscar usuario
    rows = _get("usuarios", filters={
        "username": f"eq.{username.strip()}",
        "password": f"eq.{_hash(password)}",
        "activo": "eq.true"
    })
    if not rows:
        return None

    user = rows[0]

    # Verificar suscripcion vigente
    hoy = date.today().strftime("%Y-%m-%d")
    sus = _get("suscripciones", filters={
        "usuario_id": f"eq.{user['id']}",
        "expira": f"gte.{hoy}"
    }, order="expira.desc", limit=1)

    if not sus:
        return None  # sin suscripcion o expirada

    # Crear sesion (24h)
    token = _token()
    expira = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    _post("sesiones", {"token": token, "usuario_id": user["id"], "expira": expira})
    return token


def logout(token: str):
    _delete("sesiones", {"token": f"eq.{token}"})


def get_user_from_token(token: Optional[str]) -> Optional[dict]:
    """Devuelve dict del usuario o None si el token es invalido/expirado."""
    if not token:
        return None

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Obtener sesion valida
    sesiones = _get("sesiones", filters={
        "token": f"eq.{token}",
        "expira": f"gt.{ahora}"
    }, select="usuario_id")

    if not sesiones:
        return None

    uid = sesiones[0]["usuario_id"]

    # Obtener usuario con su suscripcion
    rows = _get("usuarios", filters={"id": f"eq.{uid}"}, select="id,username,rol")
    if not rows:
        return None

    user = rows[0]

    # Obtener fecha de expiracion
    sus = _get("suscripciones", filters={"usuario_id": f"eq.{uid}"},
               select="expira", order="expira.desc", limit=1)
    user["expira"] = sus[0]["expira"] if sus else None

    return user


def suscripcion_vigente(user: dict) -> bool:
    hoy = date.today().strftime("%Y-%m-%d")
    return bool(user.get("expira") and user["expira"] >= hoy)


def dias_restantes(user: dict) -> int:
    if not user.get("expira"):
        return 0
    exp = datetime.strptime(user["expira"], "%Y-%m-%d").date()
    return max(0, (exp - date.today()).days)


# ──────────────────────────────────────────────────────────────
#  Registro
# ──────────────────────────────────────────────────────────────

def registrar(username: str, password: str, dias: int = 0, rol: str = "usuario") -> tuple[bool, str]:
    """Crea un usuario nuevo. Devuelve (ok, mensaje)."""
    if len(username) < 3:
        return False, "El usuario debe tener al menos 3 caracteres"
    if len(password) < 6:
        return False, "La contrasena debe tener al menos 6 caracteres"
    try:
        existing = _get("usuarios", filters={"username": f"eq.{username.strip()}"})
        if existing:
            return False, "Ese nombre de usuario ya existe"

        _post("usuarios", {
            "username": username.strip(),
            "password": _hash(password),
            "rol": rol,
            "activo": True,
            "creado": _now()
        })

        if dias > 0:
            uid_row = _get("usuarios", filters={"username": f"eq.{username.strip()}"})
            if uid_row:
                uid = uid_row[0]["id"]
                _post("suscripciones", {
                    "usuario_id": uid,
                    "expira": _fecha_expira(dias),
                    "creado": _now()
                })
        return True, "Usuario creado correctamente"
    except Exception as e:
        return False, f"Error creando usuario: {e}"


# ──────────────────────────────────────────────────────────────
#  Admin: gestion de usuarios
# ──────────────────────────────────────────────────────────────

def listar_usuarios() -> list[dict]:
    rows = _get("usuarios", select="id,username,rol,activo,creado", order="creado.desc")
    result = [dict(r) for r in rows]

    # Agregar fecha de expiracion
    for user in result:
        sus = _get("suscripciones", filters={"usuario_id": f"eq.{user['id']}"},
                   select="expira", order="expira.desc", limit=1)
        user["expira"] = sus[0]["expira"] if sus else None

    return result


def eliminar_usuario(uid: int):
    _delete("sesiones", {"usuario_id": f"eq.{uid}"})
    _delete("suscripciones", {"usuario_id": f"eq.{uid}"})
    _delete("usuarios", {"id": f"eq.{uid}"})


def agregar_dias(uid: int, dias: int):
    """Extiende o crea suscripcion para el usuario."""
    # Obtener suscripcion actual
    actual = _get("suscripciones", filters={"usuario_id": f"eq.{uid}"},
                  select="expira", order="expira.desc", limit=1)

    hoy = date.today()
    if actual and actual[0]["expira"] >= hoy.strftime("%Y-%m-%d"):
        base = datetime.strptime(actual[0]["expira"], "%Y-%m-%d").date()
    else:
        base = hoy

    nueva_expira = (base + timedelta(days=dias)).strftime("%Y-%m-%d")
    _post("suscripciones", {
        "usuario_id": uid,
        "expira": nueva_expira,
        "creado": _now()
    })


def toggle_activo(uid: int):
    # Obtener estado actual
    rows = _get("usuarios", filters={"id": f"eq.{uid}"}, select="activo")
    if not rows:
        return
    nuevo_estado = not rows[0]["activo"]
    _patch("usuarios", {"activo": nuevo_estado}, {"id": f"eq.{uid}"})


# ──────────────────────────────────────────────────────────────
#  Middleware helper — usar en routers
# ──────────────────────────────────────────────────────────────

def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("session")
    return get_user_from_token(token)


def require_login(request: Request) -> Optional[RedirectResponse]:
    """Devuelve RedirectResponse si no esta autenticado, None si si."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not suscripcion_vigente(user):
        return RedirectResponse("/login?expired=1", status_code=303)
    return None


def require_admin(request: Request) -> Optional[RedirectResponse]:
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.get("rol") != "admin":
        return RedirectResponse("/", status_code=303)
    return None
