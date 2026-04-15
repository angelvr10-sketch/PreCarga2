"""core/auth.py — Usuarios, sesiones y suscripciones con Supabase"""
import hashlib
import secrets
import os
import random
import re
from datetime import datetime, date, timedelta, timezone
from functools import wraps
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from core.supabase_db import (
    _get, _post, _delete, _patch, verificar_conexion, _now,
    HAS_HTTPX, httpx
)

# Constante para descargas gratis
MAX_DESCARGAS_GRATIS = 10

# Configuracion de email (debe estar en .env)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

# Rate limiting: max 3 registros por IP en 24h
MAX_REGISTROS_POR_IP = 3
VENTANA_RATE_LIMIT_HORAS = 24

# Validacion de email
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _fecha_expira(dias: int) -> str:
    return (date.today() + timedelta(days=dias)).strftime("%Y-%m-%d")


def _token() -> str:
    return secrets.token_hex(32)


def _codigo_verificacion() -> str:
    """Genera código de 6 dígitos para verificación de email."""
    return ''.join(random.choices('0123456789', k=6))


def _ip_from_request(request: Request) -> str:
    """Extrae la IP real del request, considerando proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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

def login(username_or_email: str, password: str) -> Optional[str]:
    """
    Verifica credenciales y suscripcion activa.
    Acepta username o email como identificador.
    Devuelve token de sesion o None.
    """
    entrada = username_or_email.strip()
    password_hash = _hash(password)

    # Intentar buscar por username
    rows = _get("usuarios", filters={
        "username": f"eq.{entrada}",
        "password": f"eq.{password_hash}",
        "activo": "eq.true"
    })

    # Si no encuentra, buscar por email
    if not rows:
        rows = _get("usuarios", filters={
            "email": f"eq.{entrada.lower()}",
            "password": f"eq.{password_hash}",
            "activo": "eq.true"
        })

    if not rows:
        return None

    user = rows[0]

    # Verificar suscripcion vigente (opcional - usuarios sin suscripcion pueden entrar en modo gratis)
    hoy = date.today().strftime("%Y-%m-%d")
    sus = _get("suscripciones", filters={
        "usuario_id": f"eq.{user['id']}",
        "expira": f"gte.{hoy}"
    }, order="expira.desc", limit=1)

    # Permitir login aunque no tenga suscripcion (modo gratuito con descargas)
    # if not sus:
    #     return None  # sin suscripcion o expirada

    # Crear sesion (24h)
    token = _token()
    expira = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    _post("sesiones", {"token": token, "usuario_id": user["id"], "expira": expira})
    return token


def logout(token: str):
    _delete("sesiones", {"token": f"eq.{token}"})


def get_user_from_token(token: Optional[str]) -> Optional[dict]:
    """Devuelve dict del usuario o None si el token es invalido/expirado."""
    if not token:
        return None

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Obtener sesion valida
    sesiones = _get("sesiones", filters={
        "token": f"eq.{token}",
        "expira": f"gt.{ahora}"
    }, select="usuario_id")

    if not sesiones:
        return None

    uid = sesiones[0]["usuario_id"]

    # Obtener usuario con su suscripcion
    rows = _get("usuarios", filters={"id": f"eq.{uid}"}, select="id,username,rol,descargas_usadas")
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


def _parse_fecha(fecha_str: str) -> date:
    """Parsea fecha tolerando formatos con y sin hora."""
    fecha_str = fecha_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(fecha_str, fmt).date()
        except ValueError:
            continue
    # Si ninguno funciona, intentar extraer solo la parte de fecha
    return datetime.strptime(fecha_str[:10], "%Y-%m-%d").date()


def dias_restantes(user: dict) -> int:
    if not user.get("expira"):
        return 0
    try:
        exp = _parse_fecha(user["expira"])
        return max(0, (exp - date.today()).days)
    except Exception:
        return 0


def puede_descargar(user: dict) -> tuple[bool, str]:
    """
    Verifica si el usuario puede descargar.
    Retorna (True, "") si puede, o (False, "razon") si no.
    """
    # Si tiene suscripcion vigente, puede descargar ilimitado
    if suscripcion_vigente(user):
        return True, ""

    # Verificar descargas gratis disponibles
    usadas = user.get("descargas_usadas", 0)
    if usadas < MAX_DESCARGAS_GRATIS:
        return True, ""

    return False, f"Te quedaste sin descargas gratis ({usadas}/{MAX_DESCARGAS_GRATIS}). Compra una suscripcion."


def contar_descarga(usuario_id: int):
    """Incrementa el contador de descargas usadas del usuario."""
    # Obtener valor actual
    rows = _get("usuarios", filters={"id": f"eq.{usuario_id}"}, select="descargas_usadas")
    if rows:
        actuales = rows[0].get("descargas_usadas", 0)
        _patch("usuarios", {"descargas_usadas": actuales + 1}, {"id": f"eq.{usuario_id}"})


def reset_descargas(usuario_id: int):
    """Resetea el contador de descargas (se llama cuando compra suscripcion)."""
    _patch("usuarios", {"descargas_usadas": 0}, {"id": f"eq.{usuario_id}"})


# ──────────────────────────────────────────────────────────────
#  Rate Limiting (anti-abuso de registro)
# ──────────────────────────────────────────────────────────────

def _limpiar_registros_antiguos(ip: str):
    """Elimina registros de rate limiting antiguos de la IP."""
    try:
        hace_24h = (datetime.now(timezone.utc) - timedelta(hours=VENTANA_RATE_LIMIT_HORAS)).strftime("%Y-%m-%d %H:%M:%S")
        registros = _get("rate_limit_registros", filters={
            "ip": f"eq.{ip}",
            "creado": f"lt.{hace_24h}"
        })
        for r in registros:
            _delete("rate_limit_registros", {"id": f"eq.{r['id']}"})
    except Exception:
        pass  # Ignorar errores de limpieza


def _contar_registros_recientes(ip: str) -> int:
    """Cuenta cuántos registros ha hecho esta IP en las últimas 24h."""
    try:
        hace_24h = (datetime.now(timezone.utc) - timedelta(hours=VENTANA_RATE_LIMIT_HORAS)).strftime("%Y-%m-%d %H:%M:%S")
        registros = _get("rate_limit_registros", filters={
            "ip": f"eq.{ip}",
            "creado": f"gte.{hace_24h}"
        })
        return len(registros)
    except Exception:
        return 0


def _registrar_intento(ip: str):
    """Registra un intento de registro desde esta IP."""
    try:
        _post("rate_limit_registros", {
            "ip": ip,
            "creado": _now()
        })
    except Exception:
        pass  # No bloquear registro por error de rate limiting


# ──────────────────────────────────────────────────────────────
#  Email
# ──────────────────────────────────────────────────────────────

def enviar_email(to: str, subject: str, body: str) -> bool:
    """Envia email usando SMTP configurado."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Debugging: Print SMTP credentials being used (masked password)
    print(f"SMTP Config: Host={SMTP_HOST}, Port={SMTP_PORT}, User={SMTP_USER}, From={FROM_EMAIL}")
    print(f"SMTP Password: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else 'None'}")

    if not SMTP_USER or not SMTP_PASSWORD:
        # Modo desarrollo: imprimir a consola
        print(f"\n[EMAIL SIMULADO - DESARROLLO]")
        print(f"Para: {to}")
        print(f"Asunto: {subject}")
        print(f"Cuerpo:\n{body}")
        print(f"{'='*50}\n")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"Error de autenticación SMTP (credenciales incorrectas): {e}")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"Error de conexión SMTP (servidor no accesible o puerto incorrecto): {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"Error general SMTP: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado al enviar email: {e}")
        return False


def enviar_codigo_verificacion(email: str, codigo: str) -> bool:
    """Envia el código de verificación al email del usuario."""
    subject = "Código de verificación - Precarga SHAT"
    body = f"""
Hola,

Tu código de verificación para completar el registro es:

    {codigo}

Este código expira en 30 minutos.

Si no solicitaste este registro, ignora este mensaje.

---
Precarga SHAT
"""
    return enviar_email(email, subject, body)


# ──────────────────────────────────────────────────────────────
#  Registro con verificación por email
# ──────────────────────────────────────────────────────────────

def registrar_enviar_codigo(email: str, username: str, password: str, ip: str) -> tuple[bool, str]:
    """
    Inicia el proceso de registro enviando un código de verificación al email.
    Guarda los datos temporalmente hasta que se verifique.
    """
    # Validaciones
    if not EMAIL_REGEX.match(email):
        return False, "El email no tiene un formato válido"
    if len(username) < 3:
        return False, "El usuario debe tener al menos 3 caracteres"
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres"

    # Validar que username no exista
    existing = _get("usuarios", filters={"username": f"eq.{username.strip()}"})
    if existing:
        return False, "Ese nombre de usuario ya existe"

    # Validar que email no exista
    existing_email = _get("usuarios", filters={"email": f"eq.{email.strip().lower()}"})
    if existing_email:
        return False, "Ya existe una cuenta con ese email"

    # Rate limiting por IP
    _limpiar_registros_antiguos(ip)
    intentos = _contar_registros_recientes(ip)
    if intentos >= MAX_REGISTROS_POR_IP:
        return False, f"Demasiados intentos de registro. Intenta de nuevo en {VENTANA_RATE_LIMIT_HORAS} horas."

    # Generar código de verificación
    codigo = _codigo_verificacion()
    expira = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

    # Guardar en tabla temporal (o actualizar si ya existe)
    try:
        # Verificar si ya hay un código pendiente para este email
        pendiente = _get("verificaciones_pendientes", filters={"email": f"eq.{email.strip().lower()}"})
        if pendiente:
            # Actualizar código existente
            _patch("verificaciones_pendientes", {
                "codigo": codigo,
                "expira": expira,
                "username": username.strip(),
                "password_hash": _hash(password),
                "ip": ip,
                "creado": _now()
            }, {"email": f"eq.{email.strip().lower()}"})
        else:
            # Crear nuevo
            _post("verificaciones_pendientes", {
                "email": email.strip().lower(),
                "username": username.strip(),
                "password_hash": _hash(password),
                "codigo": codigo,
                "expira": expira,
                "ip": ip,
                "creado": _now()
            })
    except Exception as e:
        return False, f"Error guardando verificación: {e}"

    # Enviar email
    if enviar_codigo_verificacion(email, codigo):
        _registrar_intento(ip)
        return True, "Código de verificación enviado. Revisa tu email."
    else:
        return False, "Error enviando el email. Intenta de nuevo más tarde."


def verificar_codigo_y_crear_cuenta(email: str, codigo: str) -> tuple[bool, str]:
    """
    Verifica el código e inserta el usuario real en la BD.
    """
    email_norm = email.strip().lower()
    codigo_norm = codigo.strip()

    # Buscar verificación pendiente
    try:
        pendiente = _get("verificaciones_pendientes", filters={
            "email": f"eq.{email_norm}",
            "codigo": f"eq.{codigo_norm}"
        })

        if not pendiente:
            return False, "Código incorrecto o email no encontrado"

        ver = pendiente[0]

        # Verificar expiración
        ahora = datetime.now(timezone.utc)
        expira_str = ver["expira"]
        # Asegurar que el timestamp tenga timezone UTC
        if expira_str and "+" not in expira_str and "T" not in expira_str:
            expira_str = expira_str + "+00:00"
        expira = datetime.fromisoformat(expira_str)
        # Convertir a UTC si tiene timezone, o asumir UTC si es naive
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
        if ahora > expira:
            # Eliminar expirado
            _delete("verificaciones_pendientes", {"id": f"eq.{ver['id']}"})
            return False, "El código ha expirado. Solicita uno nuevo."

        # Crear usuario real
        _post("usuarios", {
            "username": ver["username"],
            "email": ver["email"],
            "password": ver["password_hash"],
            "rol": "usuario",
            "activo": True,
            "email_verificado": True,
            "descargas_usadas": 0,
            "creado": _now()
        })

        # Limpiar verificación usada
        _delete("verificaciones_pendientes", {"id": f"eq.{ver['id']}"})

        return True, "Cuenta creada correctamente. Tienes 10 descargas gratis disponibles."

    except Exception as e:
        return False, f"Error verificando código: {e}"


def reenviar_codigo(email: str) -> tuple[bool, str]:
    """Reenvía el código de verificación para un email pendiente."""
    email_norm = email.strip().lower()

    try:
        pendiente = _get("verificaciones_pendientes", filters={"email": f"eq.{email_norm}"})
        if not pendiente:
            return False, "No hay registro pendiente para este email"

        ver = pendiente[0]

        # Generar nuevo código
        codigo = _codigo_verificacion()
        expira = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

        _patch("verificaciones_pendientes", {
            "codigo": codigo,
            "expira": expira
        }, {"id": f"eq.{ver['id']}"})

        if enviar_codigo_verificacion(email, codigo):
            return True, "Nuevo código enviado. Revisa tu email."
        else:
            return False, "Error enviando el email. Intenta de nuevo más tarde."

    except Exception as e:
        return False, f"Error reenviando código: {e}"


# ──────────────────────────────────────────────────────────────
#  Registro (mantener para compatibilidad y admin)
# ──────────────────────────────────────────────────────────────

def registrar(username: str, password: str, dias: int = 0, rol: str = "usuario") -> tuple[bool, str]:
    """Crea un usuario nuevo (solo para admin o compatibilidad). No requiere email."""
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
            "email_verificado": False,
            "descargas_usadas": 0,
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
        return True, "Usuario creado correctamente."
    except Exception as e:
        return False, f"Error creando usuario: {e}"


# ──────────────────────────────────────────────────────────────
#  Admin: gestion de usuarios
# ──────────────────────────────────────────────────────────────

def listar_usuarios() -> list[dict]:
    rows = _get("usuarios", select="id,username,rol,activo,descargas_usadas,creado", order="creado.desc")
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
    if actual:
        # Manejar formato con o sin hora: "2026-04-15" o "2026-04-15 00:00:00"
        expira_str = actual[0]["expira"].split(" ")[0]  # Tomar solo la fecha
        expira_date = datetime.strptime(expira_str, "%Y-%m-%d").date()
        if expira_date >= hoy:
            base = expira_date
        else:
            base = hoy
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
    # Permitir acceso aunque no tenga suscripcion (modo gratuito)
    # if not suscripcion_vigente(user):
    #     return RedirectResponse("/login?expired=1", status_code=303)
    return None


def require_admin(request: Request) -> Optional[RedirectResponse]:
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.get("rol") != "admin":
        return RedirectResponse("/", status_code=303)
    return None
