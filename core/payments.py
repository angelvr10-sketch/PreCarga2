"""core/payments.py - Integracion con MercadoPago para pagos de suscripcion"""
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Import opcional de mercadopago
try:
    import mercadopago
    HAS_MERCADOPAGO = True
except ImportError:
    HAS_MERCADOPAGO = False
    mercadopago = None

from core.auth import agregar_dias, _conn as auth_conn

# Configuracion de MercadoPago
MP_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
MP_PUBLIC_KEY = os.getenv("MERCADOPAGO_PUBLIC_KEY", "")
MP_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")
PLAN_PRICE = float(os.getenv("MERCADOPAGO_PLAN_PRICE", "499.00"))
PLAN_DAYS = int(os.getenv("MERCADOPAGO_PLAN_DAYS", "7"))
PLAN_CURRENCY = os.getenv("MERCADOPAGO_CURRENCY", "MXN")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")  # URL base para back_urls

# SDK de MercadoPago
mp = None
if HAS_MERCADOPAGO and MP_ACCESS_TOKEN:
    mp = mercadopago.SDK(MP_ACCESS_TOKEN)


def init_payments_db():
    """Crea la tabla de pagos si no existe"""
    with auth_conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            mercadopago_id TEXT UNIQUE,
            estado TEXT NOT NULL DEFAULT 'pending',
            monto REAL,
            dias_comprados INTEGER DEFAULT 7,
            creado TEXT NOT NULL,
            actualizado TEXT NOT NULL,
            notificado_mp INTEGER DEFAULT 0,
            metadata TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_pagos_usuario ON pagos(usuario_id);
        CREATE INDEX IF NOT EXISTS idx_pagos_mercadopago ON pagos(mercadopago_id);
        CREATE INDEX IF NOT EXISTS idx_pagos_estado ON pagos(estado);
        """)


def crear_preferencia(usuario_id: int, username: str) -> Dict[str, Any]:
    """Crea una preferencia de pago en MercadoPago"""
    if not mp:
        raise Exception("MercadoPago no esta configurado. Verifica MERCADOPAGO_ACCESS_TOKEN")

    # auto_return solo funciona con URLs HTTPS publicas
    is_local = "localhost" in BASE_URL or "127.0.0.1" in BASE_URL

    preference_data = {
        "items": [
            {
                "title": "Suscripcion 7 dias - Precarga SHAT",
                "quantity": 1,
                "unit_price": float(PLAN_PRICE),
                "currency_id": PLAN_CURRENCY,
            }
        ],
        "external_reference": str(usuario_id),
        "back_urls": {
            "success": f"{BASE_URL}/checkout/success",
            "failure": f"{BASE_URL}/checkout/failure",
            "pending": f"{BASE_URL}/checkout/pending"
        },
    }

    # Solo agregar payer si es un email valido
    if username and "@" in username:
        preference_data["payer"] = {"email": username}
    # No usar emails ficticios - MP los rechaza

    # auto_return solo funciona en produccion con HTTPS
    if not is_local:
        preference_data["auto_return"] = "approved"

    result = mp.preference().create(preference_data)

    print(f"DEBUG MP Response: {result}")

    if result["status"] != 201:
        error_msg = result.get('response', {}).get('message', result.get('message', 'Unknown error'))
        error_cause = result.get('response', {}).get('cause', [])
        if error_cause:
            error_msg += f" - Causes: {error_cause}"
        raise Exception(f"Error creando preferencia: {error_msg}")

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    preference_id = result["response"]["id"]

    with auth_conn() as con:
        con.execute(
            """INSERT INTO pagos (usuario_id, mercadopago_id, estado, monto,
                dias_comprados, creado, actualizado, metadata)
                VALUES (?, ?, 'pending', ?, ?, ?, ?, ?)""",
            (usuario_id, preference_id, PLAN_PRICE, PLAN_DAYS,
             ahora, ahora, json.dumps({"init_point": result["response"].get("init_point")}))
        )

    return result["response"]


def obtener_pago_mercadopago(payment_id: str) -> Dict[str, Any]:
    """Obtiene informacion de un pago desde MercadoPago"""
    if not mp:
        raise Exception("MercadoPago no esta configurado")

    result = mp.payment().get(payment_id)
    return result.get("response", {})


def procesar_notificacion_webhook(data: Dict[str, Any]) -> bool:
    """Procesa una notificacion de webhook de MercadoPago"""
    topic = data.get("topic") or data.get("type")

    if topic == "payment":
        payment_id = data.get("data", {}).get("id") or data.get("id")
        if payment_id:
            return procesar_pago(str(payment_id))

    elif topic == "merchant_order":
        order_id = data.get("data", {}).get("id") or data.get("id")
        if order_id and mp:
            order = mp.merchant_order().get(order_id)
            order_data = order.get("response", {})
            for payment in order_data.get("payments", []):
                procesar_pago(str(payment.get("id")))
            return True

    return True


def procesar_pago(payment_id: str) -> bool:
    """Procesa un pago aprobado y activa la suscripcion"""
    try:
        payment_info = obtener_pago_mercadopago(payment_id)

        if not payment_info:
            return False

        status = payment_info.get("status")
        external_ref = payment_info.get("external_reference")

        if not external_ref:
            return False

        usuario_id = int(external_ref)
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with auth_conn() as con:
            existing = con.execute(
                "SELECT id, estado FROM pagos WHERE mercadopago_id = ?",
                (payment_id,)
            ).fetchone()

            if existing and existing["estado"] == "approved":
                return True

            if existing:
                con.execute(
                    """UPDATE pagos
                        SET estado = ?, actualizado = ?, notificado_mp = 1
                        WHERE id = ?""",
                    (status, ahora, existing["id"])
                )
            else:
                preference_id = payment_info.get("preference_id")
                if preference_id:
                    pref_row = con.execute(
                        "SELECT id, usuario_id, dias_comprados FROM pagos WHERE mercadopago_id = ?",
                        (preference_id,)
                    ).fetchone()

                    if pref_row:
                        con.execute(
                            """INSERT INTO pagos (usuario_id, mercadopago_id, estado, monto,
                                dias_comprados, creado, actualizado, notificado_mp)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                            (pref_row["usuario_id"], payment_id, status,
                             payment_info.get("transaction_amount", PLAN_PRICE),
                             pref_row["dias_comprados"], ahora, ahora)
                        )
                        usuario_id = pref_row["usuario_id"]

            if status == "approved":
                dias_row = con.execute(
                    "SELECT dias_comprados FROM pagos WHERE mercadopago_id = ?",
                    (payment_id,)
                ).fetchone()

                dias = dias_row["dias_comprados"] if dias_row else PLAN_DAYS
                agregar_dias(usuario_id, dias)

        return status == "approved"

    except Exception as e:
        print(f"Error procesando pago {payment_id}: {e}")
        return False


def obtener_pagos_usuario(usuario_id: int, limit: int = 10) -> list:
    """Obtiene el historial de pagos de un usuario"""
    with auth_conn() as con:
        rows = con.execute(
            """SELECT * FROM pagos
                WHERE usuario_id = ?
                ORDER BY creado DESC
                LIMIT ?""",
            (usuario_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def obtener_ultimo_pago(usuario_id: int) -> Optional[dict]:
    """Obtiene el ultimo pago del usuario"""
    with auth_conn() as con:
        row = con.execute(
            """SELECT * FROM pagos
                WHERE usuario_id = ?
                ORDER BY creado DESC
                LIMIT 1""",
            (usuario_id,)
        ).fetchone()
    return dict(row) if row else None


def verificar_configuracion() -> bool:
    """Verifica que MercadoPago este configurado correctamente"""
    return bool(MP_ACCESS_TOKEN and mp is not None)
