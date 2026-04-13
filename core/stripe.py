"""core/stripe.py - Integracion con Stripe para pagos de suscripcion"""
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import stripe
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False
    stripe = None

from core.auth import agregar_dias, _conn as auth_conn

# Configuracion de Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE = int(float(os.getenv("STRIPE_PLAN_PRICE", "499.00")) * 100)  # Stripe usa centavos
STRIPE_DAYS = int(os.getenv("STRIPE_PLAN_DAYS", "7"))
STRIPE_CURRENCY = os.getenv("STRIPE_CURRENCY", "mxn").lower()
_raw_base = os.getenv("BASE_URL", "").strip().strip('"').strip("'").rstrip("/")
BASE_URL = _raw_base if _raw_base else "http://localhost:8000"

# Inicializar Stripe
if HAS_STRIPE and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def init_stripe_payments_db():
    """Crea la tabla de pagos_stripe si no existe"""
    with auth_conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS pagos_stripe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            stripe_session_id TEXT UNIQUE,
            stripe_payment_id TEXT,
            estado TEXT NOT NULL DEFAULT 'pending',
            monto REAL,
            dias_comprados INTEGER DEFAULT 7,
            creado TEXT NOT NULL,
            actualizado TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_stripe_usuario ON pagos_stripe(usuario_id);
        CREATE INDEX IF NOT EXISTS idx_stripe_session ON pagos_stripe(stripe_session_id);
        CREATE INDEX IF NOT EXISTS idx_stripe_payment ON pagos_stripe(stripe_payment_id);
        CREATE INDEX IF NOT EXISTS idx_stripe_estado ON pagos_stripe(estado);
        """)


def crear_checkout_session(usuario_id: int, username: str) -> Dict[str, Any]:
    """Crea una sesion de checkout en Stripe"""
    if not stripe or not STRIPE_SECRET_KEY:
        raise Exception("Stripe no esta configurado. Verifica STRIPE_SECRET_KEY")

    success_url = f"{BASE_URL}/stripe/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{BASE_URL}/stripe/cancel"

    # Validar URLs antes de enviar a Stripe
    if not BASE_URL.startswith(("http://", "https://")):
        raise Exception(f"BASE_URL invalido: '{BASE_URL}'. Debe empezar con http:// o https://")

    print(f"DEBUG: BASE_URL='{BASE_URL}'")
    print(f"DEBUG: success_url='{success_url}'")
    print(f"DEBUG: cancel_url='{cancel_url}'")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": STRIPE_CURRENCY,
                "product_data": {
                    "name": "Suscripcion 7 dias - Precarga SHAT",
                    "description": "Acceso completo al sistema Precarga SHAT por 7 dias",
                },
                "unit_amount": STRIPE_PRICE,  # En centavos
            },
            "quantity": 1,
        }],
        mode="payment",
        customer_email=username if "@" in username else None,
        metadata={
            "usuario_id": str(usuario_id),
            "dias": str(STRIPE_DAYS),
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with auth_conn() as con:
        con.execute(
            """INSERT INTO pagos_stripe (usuario_id, stripe_session_id, estado, monto,
                dias_comprados, creado, actualizado)
                VALUES (?, ?, 'pending', ?, ?, ?, ?)""",
            (usuario_id, session.id, STRIPE_PRICE / 100, STRIPE_DAYS,
             ahora, ahora)
        )

    return {
        "id": session.id,
        "url": session.url,
    }


def procesar_webhook_stripe(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """Procesa un evento de webhook de Stripe"""
    if not stripe or not STRIPE_WEBHOOK_SECRET:
        raise Exception("Webhook de Stripe no configurado")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise ValueError(f"Payload invalido: {e}")
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Firma invalida: {e}")

    return event


def procesar_evento_pago(event: Dict[str, Any]) -> bool:
    """Procesa un evento de pago de Stripe"""
    data_object = event.get("data", {}).get("object", {})
    event_type = event.get("type", "")

    if event_type not in ("checkout.session.completed", "payment_intent.succeeded"):
        return True  # Evento no relevante, pero considerado exitoso

    # Obtener session_id o payment_intent_id
    session_id = data_object.get("id")
    payment_intent = data_object.get("payment_intent")
    usuario_id = data_object.get("metadata", {}).get("usuario_id")
    payment_status = data_object.get("payment_status", "")

    if not usuario_id:
        # Intentar buscar por session_id
        with auth_conn() as con:
            row = con.execute(
                "SELECT usuario_id FROM pagos_stripe WHERE stripe_session_id = ?",
                (session_id,)
            ).fetchone()
            if row:
                usuario_id = str(row["usuario_id"])
            else:
                return False

    usuario_id = int(usuario_id)
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    monto = data_object.get("amount_total", STRIPE_PRICE) / 100

    with auth_conn() as con:
        existing = con.execute(
            "SELECT id, estado FROM pagos_stripe WHERE stripe_session_id = ?",
            (session_id,)
        ).fetchone()

        if existing:
            if existing["estado"] == "approved":
                return True  # Ya procesado

            con.execute(
                """UPDATE pagos_stripe
                    SET estado = ?, actualizado = ?, stripe_payment_id = ?, monto = ?
                    WHERE id = ?""",
                ("approved", ahora, payment_intent, monto, existing["id"])
            )
        else:
            # Crear registro si no existe
            con.execute(
                """INSERT INTO pagos_stripe (usuario_id, stripe_session_id, stripe_payment_id,
                    estado, monto, dias_comprados, creado, actualizado)
                    VALUES (?, ?, ?, 'approved', ?, ?, ?, ?)""",
                (usuario_id, session_id, payment_intent, monto, STRIPE_DAYS,
                 ahora, ahora)
            )

        # Agregar dias de suscripcion
        agregar_dias(usuario_id, STRIPE_DAYS)

    return True


def obtener_info_sesion(session_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene informacion de una sesion de Stripe"""
    if not stripe or not STRIPE_SECRET_KEY:
        return None

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": session.id,
            "payment_status": session.payment_status,
            "status": session.status,
            "payment_intent": session.payment_intent,
            "amount_total": session.amount_total,
            "customer_email": session.customer_email,
            "metadata": session.metadata,
        }
    except Exception as e:
        print(f"Error obteniendo sesion de Stripe: {e}")
        return None


def verificar_configuracion_stripe() -> bool:
    """Verifica que Stripe este configurado correctamente"""
    return bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY and stripe is not None)


def obtener_pagos_stripe_usuario(usuario_id: int, limit: int = 10) -> list:
    """Obtiene el historial de pagos con Stripe de un usuario"""
    with auth_conn() as con:
        rows = con.execute(
            """SELECT * FROM pagos_stripe
                WHERE usuario_id = ?
                ORDER BY creado DESC
                LIMIT ?""",
            (usuario_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]
