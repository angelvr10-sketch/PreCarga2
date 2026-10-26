"""core/auth.py — Usuarios, sesiones y suscripciones con Supabase"""
import bcrypt
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
    _get, _get_all, _post, _delete, _patch, verificar_conexion, _now,
    SUPABASE_URL, KEY_TIPO,
    HAS_HTTPX, httpx
)

# Constante para descargas gratis
MAX_DESCARGAS_GRATIS = 30

# Configuracion de email via Resend (debe estar en .env)
#
# El .strip() no es cosmetico: una clave con un espacio al final (muy facil de
# colar al copiar, y el .env la deja entre comillas) produce la cabecera
# "Bearer re_xxx " y httpx lanza LocalProtocolError: Illegal header value,
# sin llegar a pegarle a la API de Resend. El error es de conexion, no de
# credencial, asi que no dice nada de la clave.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", "Precarga <noreply@precarga.com>").strip()

# Brevo (ex Sendinblue). A diferencia de Resend, Brevo deja verificar una
# direccion de correo individual sin comprar ni verificar un dominio, asi que
# es la opcion cuando todavia no hay dominio propio.
#
# El .strip() tambien aqui no es cosmetico: un espacio al final en la clave
# hace que Brevo responda 401 en vez de decir que la clave no es valida.
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Precarga").strip()
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "").strip()

# Brevo por SMTP. Se deja esta via porque el login se ve siempre en el panel y
# la SMTP key se revela con un clic, mientras que la API key solo se muestra una
# vez al crearla. El usuario con el que se entra es un identificador propio de
# Brevo (algo@smtp-brevo.com), NO es el correo remitente.
BREVO_SMTP_HOST = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com").strip()
BREVO_SMTP_PORT = int(os.getenv("BREVO_SMTP_PORT", "587") or 587)
BREVO_SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN", "").strip()
BREVO_SMTP_PASSWORD = os.getenv("BREVO_SMTP_PASSWORD", "").strip()

# Envio directo por el SMTP de un Gmail propio. Esta es la unica via que no
# pide ni cuenta en un proveedor de email ni dominio: se usa cuando todavia
# no se tiene un numero de telefono para verificar la cuenta de Brevo.
#
# ADVERTENCIA: es comodo para desarrollo pero NO para produccion. Google corta
# el envio si detecta volumen anomalo o si la cuenta corre riesgo de compromiso,
# y ademas queda atado a una cuenta personal. Para produccion, un dominio y un
# proveedor serio.
GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
GMAIL_SMTP_HOST = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com").strip()
GMAIL_SMTP_PORT = int(os.getenv("GMAIL_SMTP_PORT", "465") or 465)

# Rate limiting: max 3 registros por IP en 24h
MAX_REGISTROS_POR_IP = 3
VENTANA_RATE_LIMIT_HORAS = 24

# Validacion de email
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Recuperacion de contrasena. Se reutiliza `verificaciones_pendientes`, que ya
# guarda codigos temporales de 6 digitos, con un marcador en `username` para
# distinguir un reset de un registro. Las dos operaciones son mutuamente
# excluyentes por email: un reset solo aplica a una cuenta existente y un
# registro solo a un email que aun no existe.
RESET_MARKER = "__reset_password__"
RESET_MINUTOS_EXPIRA = 30
RESET_SEGUNDOS_ESPERA = 60
RESET_MAX_SOLICITUDES_HORA = 5
RESET_MAX_INTENTOS = 10
RESEND_MAX_POR_HORA = 3


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    """Genera hash usando bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')


def _verify_password(password: str, hashed: str) -> bool:
    """Verifica contraseña contra hash de bcrypt."""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode('utf-8'))
    except Exception:
        return False


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
    print(f"Supabase: {SUPABASE_URL or '(sin URL)'} | clave={KEY_TIPO}")
    if not verificar_conexion():
        print("WARNING: No se pudo conectar a Supabase. Verifica SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY")
        return

    # Crear admin por defecto si no existe.
    # Un fallo aqui no debe tumbar el servidor: la app puede seguir sirviendo
    # login y el admin se puede crear despues a mano.
    try:
        existing = _get("usuarios", filters={"username": "eq.admin"})
        if existing:
            print("Conexion a Supabase exitosa")
            return

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
    except Exception as e:
        print(f"\nERROR: no se pudo inicializar el usuario admin en Supabase: {e}")
        print("Si el mensaje menciona 'row-level security', agrega "
              "SUPABASE_SERVICE_ROLE_KEY al .env (la anon key no puede escribir).")


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

    # Buscar usuario por username o email
    rows = _get("usuarios", filters={
        "username": f"eq.{entrada}",
        "activo": "eq.true"
    })

    if not rows:
        rows = _get("usuarios", filters={
            "email": f"eq.{entrada.lower()}",
            "activo": "eq.true"
        })

    if not rows:
        return None

    user = rows[0]

    # Verificar contraseña con bcrypt
    if not _verify_password(password, user['password']):
        return None

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


def cambiar_password(usuario_id, actual: str, nueva: str) -> tuple[bool, str]:
    """Cambia la contrasena del propio usuario.

    Devuelve (ok, token_nuevo | mensaje_de_error). Al cambiarla se cierran
    TODAS las sesiones del usuario, incluidas otras pestanas o dispositivos,
    y se emite un token nuevo para la sesion desde la que se hizo el cambio.
    Asi una contrasena filtrada deja de servir de inmediato.
    """
    if len(nueva) < 6:
        return False, "La nueva contrasena debe tener al menos 6 caracteres"
    if len(nueva) > 128:
        return False, "La nueva contrasena es demasiado larga"

    rows = _get("usuarios", filters={"id": f"eq.{usuario_id}"}, select="password")
    if not rows:
        return False, "Usuario no encontrado"

    hash_actual = rows[0].get("password") or ""
    if not _verify_password(actual, hash_actual):
        return False, "La contrasena actual no es correcta"
    if _verify_password(nueva, hash_actual):
        return False, "La nueva contrasena debe ser diferente a la actual"

    try:
        _patch("usuarios", {"password": _hash(nueva)}, {"id": f"eq.{usuario_id}"})
        _delete("sesiones", {"usuario_id": f"eq.{usuario_id}"})

        token = _token()
        expira = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        _post("sesiones", {"token": token, "usuario_id": usuario_id, "expira": expira})
        return True, token
    except Exception as e:
        return False, f"Error cambiando la contrasena: {e}"


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
    rows = _get("usuarios", filters={"id": f"eq.{uid}"},
                select="id,username,email,rol,activo,email_verificado,creado,descargas_usadas")
    if not rows:
        return None

    user = rows[0]

    # Un usuario desactivado pierde la sesion en la siguiente peticion. Antes
    # `activo` solo se revisaba al hacer login, asi que desactivar a alguien
    # no lo sacaba: seguia entrando con el token que ya tenia en la cookie.
    if not user.get("activo", True):
        return None

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


def _clave_evento(clave: str) -> str:
    """Ajusta la clave al ancho de `rate_limit_registros.ip` (VARCHAR(45)).

    Las claves con prefijo ("reset-verify:<ipv6>", "resend:<email>") pueden
    superar 45 caracteres. PostgREST rechaza el INSERT con "value too long",
    y como `_registrar_evento` traga la excepcion, el limite se apagaba en
    silencio para IPv6 y correos largos. Se guarda un hash estable en esos
    casos; el conteo usa la misma transformacion, asi que sigue cuadrando.
    """
    if len(clave) <= 45:
        return clave
    return "h:" + hashlib.sha256(clave.encode("utf-8")).hexdigest()[:43]


def _registrar_evento(clave: str):
    """Registra un evento de rate limit con una clave propia.

    `rate_limit_registros` solo tiene `ip` y `creado`, asi que se usan claves
    con prefijo ("reset-req:1.2.3.4") para no mezclar estos conteos con los
    del registro normal, que consulta la IP exacta.
    """
    clave = _clave_evento(clave)
    try:
        _delete("rate_limit_registros", {
            "ip": f"eq.{clave}",
            "creado": f"lt.{(datetime.now(timezone.utc) - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')}",
        })
        _post("rate_limit_registros", {"ip": clave, "creado": _now()})
    except Exception:
        pass


def _contar_eventos(clave: str, horas: int = 1) -> int:
    clave = _clave_evento(clave)
    desde = (datetime.now(timezone.utc) - timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        rows = _get("rate_limit_registros", filters={
            "ip": f"eq.{clave}",
            "creado": f"gte.{desde}",
        })
        return len(rows)
    except Exception:
        return 0


# ──────────────────────────────────────────────────────────────
#  Email
# ──────────────────────────────────────────────────────────────

def _email_desarrollo(to: str, subject: str, body: str) -> bool:
    """Sin proveedor configurado: imprime el correo en la consola del servidor.

    Es lo que permite probar el flujo de registro en local sin depender de
    Resend ni de Brevo. Nunca debe quedar activo en produccion.
    """
    print(f"\n[EMAIL SIMULADO - DESARROLLO]")
    print(f"Para: {to}")
    print(f"Asunto: {subject}")
    print(f"Cuerpo:\n{body}")
    print(f"{'='*50}\n")
    return True


def _enviar_resend(to: str, subject: str, body: str) -> bool:
    """Resend exige un dominio verificado, asi que necesita FROM_EMAIL real."""
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "text": body,
        },
        timeout=10.0,
    )
    if response.status_code in (200, 201):
        return True
    print(f"[EMAIL] Resend fallo [{response.status_code}] desde={FROM_EMAIL}: {response.text}")
    return False


def _enviar_brevo_smtp(to: str, subject: str, body: str) -> bool:
    """Envio por SMTP de Brevo (smtp-relay.brevo.com:587 + STARTTLS).

    El login es un identificador propio de Brevo del tipo algo@smtp-brevo.com
    y la password es la SMTP key, que NO es lo mismo que la API key.
    """
    import smtplib
    from email.message import EmailMessage
    from email.utils import formataddr

    msg = EmailMessage()
    msg["From"] = formataddr((BREVO_SENDER_NAME, BREVO_SENDER_EMAIL))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(BREVO_SMTP_HOST, BREVO_SMTP_PORT, timeout=15.0) as srv:
            srv.ehlo()
            # El relay de Brevo en 587 exige STARTTLS; en 465 ya viene TLS.
            if BREVO_SMTP_PORT == 465:
                srv.starttls()
            else:
                srv.starttls()
            srv.ehlo()
            srv.login(BREVO_SMTP_LOGIN, BREVO_SMTP_PASSWORD)
            srv.send_message(msg)
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL] Brevo SMTP: usuario o password incorrectos ({e.smtp_code}). "
              f"Revisar BREVO_SMTP_LOGIN y BREVO_SMTP_PASSWORD.")
        return False
    except Exception as e:
        print(f"[EMAIL] Brevo SMTP fallo: {type(e).__name__}: {e}")
        if isinstance(e, TimeoutError):
            print("[EMAIL] Render free bloquea los puertos SMTP (25/465/587). "
                  "Configura BREVO_API_KEY para enviar por HTTPS.")
        return False


def _enviar_gmail(to: str, subject: str, body: str) -> bool:
    """Envio directo por SMTP de Gmail.

    Requiere activacion en dos pasos con verificacion por app y una contrasena
    de aplicacion. El puerto 465 usa TLS directo (SMTP_SSL) y el 587 usa
    STARTTLS.
    """
    import smtplib
    from email.message import EmailMessage
    from email.utils import formataddr

    msg = EmailMessage()
    msg["From"] = formataddr((BREVO_SENDER_NAME, GMAIL_USER))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if GMAIL_SMTP_PORT == 465:
            srv = smtplib.SMTP_SSL(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=15.0)
        else:
            srv = smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=15.0)
        with srv:
            srv.ehlo()
            if GMAIL_SMTP_PORT != 465:
                srv.starttls()
                srv.ehlo()
            srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            srv.send_message(msg)
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL] Gmail: autenticacion fallida ({e.smtp_code}). Las causas "
              f"habituales son una contrasena de aplicacion incorrecta o que la "
              f"verificacion en dos pasos este desactivada.")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL] Gmail SMTP fallo: {type(e).__name__}: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL] Gmail fallo: {type(e).__name__}: {e}")
        return False


def _enviar_brevo(to: str, subject: str, body: str) -> bool:
    """Brevo permite verificar un remitente suelto sin dominio (API v3 /smtp/email)."""
    response = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": BREVO_API_KEY,
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={
            "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
            "to": [{"email": to}],
            "subject": subject,
            "text": body,
        },
        timeout=10.0,
    )
    if response.status_code in (200, 201):
        return True
    print(f"[EMAIL] Brevo fallo [{response.status_code}] desde={BREVO_SENDER_EMAIL}: {response.text}")
    return False


def enviar_email(to: str, subject: str, body: str) -> bool:
    """Envia un email transaccional por el proveedor que este configurado.

    Se priorizan las APIs HTTP (puerto 443) sobre SMTP porque Render free
    bloquea los puertos 25, 465 y 587: el SMTP local funciona, pero en
    produccion se queda en TimeoutError. Si un proveedor configurado falla,
    se intenta el siguiente antes de rendirse.

    Los proveedores devuelven 401 con una clave invalida, pero el mensaje no
    siempre lo aclara; por eso cada rama loguea remitente y respuesta, que es
    lo primero que hay que mirar cuando "el registro no funciona".
    """
    configurado = False

    # 1. Brevo por API (HTTPS). Es la via que funciona en Render free.
    if BREVO_API_KEY:
        configurado = True
        if not BREVO_SENDER_EMAIL:
            print("[EMAIL] BREVO_API_KEY esta puesto pero falta BREVO_SENDER_EMAIL.")
        elif not HAS_HTTPX:
            print("[EMAIL] httpx no instalado. Ejecuta: pip install httpx")
        else:
            try:
                if _enviar_brevo(to, subject, body):
                    return True
            except Exception as e:
                print(f"[EMAIL] error inesperado con Brevo API: {e}")
            print("[EMAIL] Brevo API fallo; se prueban otros proveedores.")

    # 2. Resend por API (HTTPS).
    if RESEND_API_KEY:
        configurado = True
        if not HAS_HTTPX:
            print("[EMAIL] httpx no instalado. Ejecuta: pip install httpx")
        else:
            try:
                if _enviar_resend(to, subject, body):
                    return True
            except Exception as e:
                print(f"[EMAIL] error inesperado con Resend: {e}")
            print("[EMAIL] Resend fallo; se prueban otros proveedores.")

    # 3. Gmail propio. Util en local, pero tambien usa SMTP.
    if GMAIL_USER and GMAIL_APP_PASSWORD:
        configurado = True
        if _enviar_gmail(to, subject, body):
            return True
        print("[EMAIL] Gmail fallo; se prueban otros proveedores.")

    # 4. Brevo por SMTP. Solo sirve si el host no bloquea esos puertos.
    if BREVO_SMTP_LOGIN and BREVO_SMTP_PASSWORD:
        configurado = True
        if not BREVO_SENDER_EMAIL:
            print("[EMAIL] falta BREVO_SENDER_EMAIL: no se puede construir el remitente.")
        elif _enviar_brevo_smtp(to, subject, body):
            return True

    if configurado:
        print("[EMAIL] Ningun proveedor pudo enviar el correo.")
        return False

    return _email_desarrollo(to, subject, body)


def enviar_codigo_verificacion(email: str, codigo: str) -> bool:
    """Envia el código de verificación al email del usuario."""
    subject = "Código de verificación - Precarga"
    body = f"""
Hola,

Tu código de verificación para completar el registro es:

    {codigo}

Este código expira en 30 minutos.

Si no solicitaste este registro, ignora este mensaje.

---
Precarga
"""
    return enviar_email(email, subject, body)


def enviar_codigo_recuperacion(email: str, codigo: str) -> bool:
    """Envia el código para restablecer la contraseña."""
    subject = "Restablecer contraseña - Precarga"
    body = f"""
Hola,

Recibimos una solicitud para restablecer la contraseña de tu cuenta.

Tu código de recuperación es:

    {codigo}

Este código expira en {RESET_MINUTOS_EXPIRA} minutos y solo puede usarse una vez.

Si no solicitaste este cambio, ignora este mensaje: tu contraseña actual
seguirá funcionando.

---
Precarga
"""
    return enviar_email(email, subject, body)


# ──────────────────────────────────────────────────────────────
#  Recuperacion de contrasena
# ──────────────────────────────────────────────────────────────

def solicitar_recuperacion(email: str, ip: str) -> tuple[bool, str]:
    """Envia (o simula enviar) un codigo de recuperacion.

    Responde SIEMPRE lo mismo exista o no la cuenta, para que el endpoint no
    sirva para averiguar que correos estan registrados. Los fallos de envio
    se loguean en el servidor, no se devuelven al cliente.
    """
    email_norm = (email or "").strip().lower()
    if not EMAIL_REGEX.match(email_norm):
        return False, "El correo no tiene un formato válido"

    generico = (
        "Si el correo está registrado, enviamos un código para restablecer la contraseña. "
        "Revisa tu bandeja de entrada y la carpeta de spam."
    )

    clave_ip = f"reset-req:{ip}"
    if _contar_eventos(clave_ip) >= RESET_MAX_SOLICITUDES_HORA:
        return True, generico
    _registrar_evento(clave_ip)

    try:
        usuarios = _get("usuarios", filters={"email": f"eq.{email_norm}"},
                        select="id,username,activo")
    except Exception as e:
        print(f"[RESET] error consultando usuario: {e}")
        return True, generico

    if not usuarios or not usuarios[0].get("activo", True):
        return True, generico

    user = usuarios[0]

    # Evita que un doble clic mande dos correos y gaste cuota del proveedor.
    try:
        pendiente = _get("verificaciones_pendientes",
                         filters={"email": f"eq.{email_norm}"})
        if pendiente and pendiente[0].get("creado"):
            try:
                creado = datetime.fromisoformat(
                    str(pendiente[0]["creado"]).replace("Z", "+00:00")
                )
                if creado.tzinfo is None:
                    creado = creado.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - creado).total_seconds() < RESET_SEGUNDOS_ESPERA:
                    return True, generico
            except (TypeError, ValueError):
                pass
    except Exception:
        pendiente = []

    codigo = _codigo_verificacion()
    expira = (datetime.now(timezone.utc) + timedelta(minutes=RESET_MINUTOS_EXPIRA)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    fila = {
        "email": email_norm,
        "username": RESET_MARKER,
        "password_hash": "",
        "codigo": codigo,
        "expira": expira,
        "ip": ip,
        "creado": _now(),
    }

    try:
        if pendiente:
            _patch("verificaciones_pendientes", fila, {"email": f"eq.{email_norm}"})
        else:
            _post("verificaciones_pendientes", fila)
    except Exception as e:
        print(f"[RESET] no se pudo guardar el código: {e}")
        return True, generico

    if not enviar_codigo_recuperacion(email_norm, codigo):
        # Si el proveedor falla, se borra el código para no dejar uno valido
        # que el usuario no recibio. El cliente ve el mensaje generico igual.
        try:
            _delete("verificaciones_pendientes", {"email": f"eq.{email_norm}"})
        except Exception:
            pass

    return True, generico


def restablecer_password(email: str, codigo: str, nueva: str, ip: str) -> tuple[bool, str]:
    """Valida el codigo y cambia la contraseña. Cierra todas las sesiones."""
    email_norm = (email or "").strip().lower()
    codigo_norm = (codigo or "").strip()

    if len(nueva) < 6:
        return False, "La nueva contraseña debe tener al menos 6 caracteres"
    if len(nueva) > 128:
        return False, "La nueva contraseña es demasiado larga"

    clave_intentos = f"reset-verify:{ip}"
    if _contar_eventos(clave_intentos) >= RESET_MAX_INTENTOS:
        return False, "Demasiados intentos. Solicita un código nuevo más tarde."

    try:
        pendientes = _get("verificaciones_pendientes",
                          filters={"email": f"eq.{email_norm}"},
                          order="creado.desc", limit=1)
    except Exception as e:
        print(f"[RESET] error leyendo código: {e}")
        return False, "No se pudo validar el código. Intenta de nuevo."

    if not pendientes or pendientes[0].get("username") != RESET_MARKER:
        _registrar_evento(clave_intentos)
        return False, "El código es incorrecto o expiró. Solicita uno nuevo."

    fila = pendientes[0]

    expira_str = str(fila.get("expira") or "").replace("Z", "+00:00")
    try:
        expira = datetime.fromisoformat(expira_str)
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
    except ValueError:
        expira = datetime.now(timezone.utc)

    if datetime.now(timezone.utc) > expira:
        _delete("verificaciones_pendientes", {"id": f"eq.{fila['id']}"})
        return False, "El código expiró. Solicita uno nuevo."

    if not secrets.compare_digest(str(fila.get("codigo") or ""), codigo_norm):
        _registrar_evento(clave_intentos)
        return False, "El código es incorrecto o expiró. Solicita uno nuevo."

    usuarios = _get("usuarios", filters={"email": f"eq.{email_norm}"},
                    select="id,activo")
    if not usuarios or not usuarios[0].get("activo", True):
        _delete("verificaciones_pendientes", {"id": f"eq.{fila['id']}"})
        return False, "No se pudo restablecer la contraseña. Contacta al administrador."

    uid = usuarios[0]["id"]
    try:
        _patch("usuarios", {"password": _hash(nueva)}, {"id": f"eq.{uid}"})
        # Todas las sesiones, incluidas las de otros dispositivos.
        _delete("sesiones", {"usuario_id": f"eq.{uid}"})
        _delete("verificaciones_pendientes", {"id": f"eq.{fila['id']}"})
    except Exception as e:
        print(f"[RESET] error actualizando la contraseña: {e}")
        return False, "No se pudo restablecer la contraseña. Intenta de nuevo."

    return True, "Contraseña actualizada. Ya puedes iniciar sesión."


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

        # Un codigo de recuperacion vive en la misma tabla (ver RESET_MARKER).
        # Si alguien lo escribe en la pantalla de verificacion de registro, no
        # debe crear una cuenta con el centinela como nombre de usuario.
        if ver.get("username") == RESET_MARKER:
            return False, "Ese código es para restablecer contraseña. Usa la opción de recuperación."

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
    email_norm = (email or "").strip().lower()
    if not EMAIL_REGEX.match(email_norm):
        return False, "El correo no tiene un formato válido"

    clave = f"resend:{email_norm}"
    if _contar_eventos(clave) >= RESEND_MAX_POR_HORA:
        return False, "Demasiados reenvíos. Intenta de nuevo en una hora."

    try:
        pendiente = _get("verificaciones_pendientes", filters={"email": f"eq.{email_norm}"})
        if not pendiente:
            return False, "No hay registro pendiente para este email"

        ver = pendiente[0]

        if ver.get("username") == RESET_MARKER:
            return False, "Ese código es de recuperación de contraseña. Solicítalo desde esa pantalla."

        # Generar nuevo código
        codigo = _codigo_verificacion()
        expira = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

        _patch("verificaciones_pendientes", {
            "codigo": codigo,
            "expira": expira,
            "creado": _now(),
        }, {"id": f"eq.{ver['id']}"})

        _registrar_evento(clave)

        if enviar_codigo_verificacion(email_norm, codigo):
            return True, "Nuevo código enviado. Revisa tu email."
        else:
            return False, "Error enviando el email. Intenta de nuevo más tarde."

    except Exception as e:
        return False, f"Error reenviando código: {e}"


# ──────────────────────────────────────────────────────────────
#  Registro (mantener para compatibilidad y admin)
# ──────────────────────────────────────────────────────────────

def registrar(username: str, password: str, dias: int = 0, rol: str = "usuario",
              email: Optional[str] = None) -> tuple[bool, str]:
    """Crea un usuario nuevo (solo para admin o compatibilidad).

    `email` es opcional para no romper llamadas antiguas, pero el panel de
    administracion lo manda siempre: sin email el usuario no puede recuperar
    la cuenta ni aparece identificable en el listado. Un usuario creado desde
    el panel se marca como verificado de una vez; el admin ya lo dio de alta.
    """
    username = username.strip()
    if len(username) < 3:
        return False, "El usuario debe tener al menos 3 caracteres"
    if len(password) < 6:
        return False, "La contrasena debe tener al menos 6 caracteres"
    if rol not in ("admin", "usuario", "lector"):
        return False, "Rol invalido"

    email = (email or "").strip().lower() or None
    if email and not EMAIL_REGEX.match(email):
        return False, "El correo no es valido"

    try:
        existing = _get("usuarios", filters={"username": f"eq.{username}"})
        if existing:
            return False, "Ese nombre de usuario ya existe"

        if email:
            if _get("usuarios", filters={"email": f"eq.{email}"}):
                return False, "Ese correo ya esta registrado"

        payload = {
            "username": username,
            "password": _hash(password),
            "rol": rol,
            "activo": True,
            "email_verificado": bool(email),
            "descargas_usadas": 0,
            "creado": _now(),
        }
        if email:
            payload["email"] = email
        _post("usuarios", payload)

        if dias > 0:
            uid_row = _get("usuarios", filters={"username": f"eq.{username}"})
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
    """Listado completo para el panel de administracion.

    Antes se hacia una consulta a `suscripciones` POR USUARIO (N+1): con 50
    usuarios eran 51 viajes a Supabase para pintar una tabla. Ahora son dos
    consultas fijas, y el SELECT incluye email y estado, que el panel mostraba
    siempre vacio/desactivado porque nunca se pedian.
    """
    rows = _get(
        "usuarios",
        select="id,username,email,rol,activo,email_verificado,descargas_usadas,creado",
        order="creado.desc",
    )
    result = [dict(r) for r in rows]

    # `order=expira.desc` + quedarse con la primera por usuario evita el N+1.
    # _get_all pagina, asi que no se trunca en el cap de 1000 filas.
    suscripciones = _get_all(
        "suscripciones", select="usuario_id,expira", order="expira.desc",
    )
    expira_por_usuario: dict = {}
    for sus in suscripciones:
        uid = sus.get("usuario_id")
        if uid not in expira_por_usuario:
            expira_por_usuario[uid] = sus.get("expira")

    for user in result:
        user["expira"] = expira_por_usuario.get(user["id"])

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