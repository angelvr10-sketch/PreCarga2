"""core/auth.py — Usuarios, sesiones y suscripciones con SQLite"""
import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from functools import wraps
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

DB_PATH = Path("data/usuarios.db")


# ──────────────────────────────────────────────────────────────
#  Conexión y esquema
# ──────────────────────────────────────────────────────────────

def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    """Crea las tablas si no existen y el admin por defecto."""
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            rol       TEXT NOT NULL DEFAULT 'usuario',
            activo    INTEGER NOT NULL DEFAULT 1,
            creado    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS suscripciones (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            expira     TEXT NOT NULL,
            creado     TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sesiones (
            token      TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            expira     TEXT NOT NULL
        );
        """)

        # Admin por defecto si no existe
        existe = con.execute(
            "SELECT id FROM usuarios WHERE username = 'admin'"
        ).fetchone()
        if not existe:
            con.execute(
                "INSERT INTO usuarios (username, password, rol, activo, creado) VALUES (?,?,?,1,?)",
                ("admin", _hash("admin123"), "admin", _now())
            )
            # Suscripción de 3650 días para el admin
            uid = con.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone()["id"]
            con.execute(
                "INSERT INTO suscripciones (usuario_id, expira, creado) VALUES (?,?,?)",
                (uid, _fecha_expira(3650), _now())
            )


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fecha_expira(dias: int) -> str:
    return (date.today() + timedelta(days=dias)).strftime("%Y-%m-%d")


def _token() -> str:
    return secrets.token_hex(32)


# ──────────────────────────────────────────────────────────────
#  Autenticación
# ──────────────────────────────────────────────────────────────

def login(username: str, password: str) -> Optional[str]:
    """
    Verifica credenciales y suscripción activa.
    Devuelve token de sesión o None.
    """
    with _conn() as con:
        user = con.execute(
            "SELECT * FROM usuarios WHERE username=? AND password=? AND activo=1",
            (username.strip(), _hash(password))
        ).fetchone()

        if not user:
            return None

        # Verificar suscripción vigente
        hoy = date.today().strftime("%Y-%m-%d")
        sus = con.execute(
            "SELECT expira FROM suscripciones WHERE usuario_id=? AND expira >= ? ORDER BY expira DESC LIMIT 1",
            (user["id"], hoy)
        ).fetchone()

        if not sus:
            return None  # sin suscripción o expirada

        # Crear sesión (24h)
        token  = _token()
        expira = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        con.execute(
            "INSERT INTO sesiones (token, usuario_id, expira) VALUES (?,?,?)",
            (token, user["id"], expira)
        )
        return token


def logout(token: str):
    with _conn() as con:
        con.execute("DELETE FROM sesiones WHERE token=?", (token,))


def get_user_from_token(token: Optional[str]) -> Optional[dict]:
    """Devuelve dict del usuario o None si el token es inválido/expirado."""
    if not token:
        return None
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as con:
        row = con.execute("""
            SELECT u.id, u.username, u.rol,
                   (SELECT expira FROM suscripciones
                    WHERE usuario_id=u.id ORDER BY expira DESC LIMIT 1) AS expira
            FROM sesiones s
            JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.token=? AND s.expira > ?
        """, (token, ahora)).fetchone()
    if not row:
        return None
    return dict(row)


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
        return False, "La contraseña debe tener al menos 6 caracteres"
    try:
        with _conn() as con:
            con.execute(
                "INSERT INTO usuarios (username, password, rol, activo, creado) VALUES (?,?,?,1,?)",
                (username.strip(), _hash(password), rol, _now())
            )
            if dias > 0:
                uid = con.execute("SELECT id FROM usuarios WHERE username=?", (username,)).fetchone()["id"]
                con.execute(
                    "INSERT INTO suscripciones (usuario_id, expira, creado) VALUES (?,?,?)",
                    (uid, _fecha_expira(dias), _now())
                )
        return True, "Usuario creado correctamente"
    except sqlite3.IntegrityError:
        return False, "Ese nombre de usuario ya existe"


# ──────────────────────────────────────────────────────────────
#  Admin: gestión de usuarios
# ──────────────────────────────────────────────────────────────

def listar_usuarios() -> list[dict]:
    with _conn() as con:
        rows = con.execute("""
            SELECT u.id, u.username, u.rol, u.activo, u.creado,
                   (SELECT expira FROM suscripciones
                    WHERE usuario_id=u.id ORDER BY expira DESC LIMIT 1) AS expira
            FROM usuarios u ORDER BY u.creado DESC
        """).fetchall()
    return [dict(r) for r in rows]


def eliminar_usuario(uid: int):
    with _conn() as con:
        con.execute("DELETE FROM sesiones WHERE usuario_id=?", (uid,))
        con.execute("DELETE FROM suscripciones WHERE usuario_id=?", (uid,))
        con.execute("DELETE FROM usuarios WHERE id=?", (uid,))


def agregar_dias(uid: int, dias: int):
    """Extiende o crea suscripción para el usuario."""
    with _conn() as con:
        actual = con.execute(
            "SELECT expira FROM suscripciones WHERE usuario_id=? ORDER BY expira DESC LIMIT 1",
            (uid,)
        ).fetchone()

        hoy = date.today()
        if actual and actual["expira"] >= hoy.strftime("%Y-%m-%d"):
            base = datetime.strptime(actual["expira"], "%Y-%m-%d").date()
        else:
            base = hoy

        nueva_expira = (base + timedelta(days=dias)).strftime("%Y-%m-%d")
        con.execute(
            "INSERT INTO suscripciones (usuario_id, expira, creado) VALUES (?,?,?)",
            (uid, nueva_expira, _now())
        )


def toggle_activo(uid: int):
    with _conn() as con:
        con.execute(
            "UPDATE usuarios SET activo = CASE WHEN activo=1 THEN 0 ELSE 1 END WHERE id=?",
            (uid,)
        )


# ──────────────────────────────────────────────────────────────
#  Middleware helper — usar en routers
# ──────────────────────────────────────────────────────────────

def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("session")
    return get_user_from_token(token)


def require_login(request: Request) -> Optional[RedirectResponse]:
    """Devuelve RedirectResponse si no está autenticado, None si sí."""
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
