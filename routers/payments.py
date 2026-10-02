"""routers/payments.py - Endpoints de pago con Stripe (API JSON)"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.auth import get_current_user, require_login
from core.stripe import (
    crear_checkout_session, procesar_webhook_stripe, procesar_evento_pago,
    obtener_info_sesion, verificar_configuracion_stripe,
    STRIPE_PRICE,
)

router = APIRouter()


# ── Crear Stripe Checkout Session ─────────────────────────────
@router.post("/api/checkout/stripe/create")
async def checkout_stripe_create(request: Request):
    """Crea una sesion de checkout con Stripe"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    if not verificar_configuracion_stripe():
        return JSONResponse({"ok": False, "error": "Stripe no configurado. Verifica STRIPE_SECRET_KEY"})

    try:
        result = crear_checkout_session(user["id"], user["username"])
        return JSONResponse({
            "ok": True,
            "session_id": result["id"],
            "url": result["url"],
        })
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"DEBUG: Error creando sesion de Stripe: {error_detail}")
        return JSONResponse({"ok": False, "error": str(e), "detail": error_detail})


# ── Webhook Stripe ───────────────────────────────────────────
@router.post("/webhook/stripe")
async def webhook_stripe(request: Request):
    """Webhook para notificaciones de Stripe

    Stripe usa signatures en el header Stripe-Signature.
    Este endpoint debe estar en HTTPS para produccion.
    """
    try:
        body = await request.body()
        sig_header = request.headers.get("stripe-signature", "")

        event = procesar_webhook_stripe(body, sig_header)
        resultado = procesar_evento_pago(event)

        if resultado:
            return JSONResponse({"status": "ok"}, status_code=200)
        else:
            return JSONResponse({"status": "error"}, status_code=500)

    except Exception as e:
        print(f"Error en webhook de Stripe: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ── Confirmacion de pago (fallback si el webhook no llega) ─────
@router.get("/api/stripe/success")
async def stripe_success(request: Request, session_id: str = None):
    """Confirma el pago de una sesion de Stripe.

    El webhook es la via principal. Este endpoint existe como red de
    seguridad: si el webhook no llega (tipico en desarrollo, o si el
    usuario cierra la pestana antes de que Stripe responda), el frontend
    lo llama al volver del redirect y el pago se procesa igual.
    """
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    if not session_id:
        return JSONResponse({"ok": True, "approved": False, "payment_status": None})

    payment_info = None
    approved = False

    try:
        payment_info = obtener_info_sesion(session_id)
        status = payment_info.get("payment_status") if payment_info else None

        if status in ("paid", "no_payment_required"):
            # Procesar el pago directamente (puede que el webhook no llegue)
            event = {"type": "checkout.session.completed", "data": {"object": payment_info}}
            procesar_evento_pago(event)
            approved = True

        elif status == "unpaid":
            # Stripe redirigio pero el pago sigue pendiente
            approved = False

        else:
            # No pudimos obtener info de Stripe, pero intentamos procesar
            # usando el registro que ya se creo en la DB
            fake_info = {
                "id": session_id,
                "payment_status": "unknown",
                "amount_total": STRIPE_PRICE,
                "metadata": {},
            }
            event = {"type": "checkout.session.completed", "data": {"object": fake_info}}
            approved = bool(procesar_evento_pago(event))

    except Exception as e:
        import traceback
        print(f"Error procesando pago en success: {e}")
        print(traceback.format_exc())
        return JSONResponse(
            {"ok": False, "error": str(e), "approved": False},
            status_code=500,
        )

    return JSONResponse({
        "ok": True,
        "approved": approved,
        "payment_status": payment_info.get("payment_status") if payment_info else None,
    })


# ── Cancelacion de pago ───────────────────────────────────────
@router.get("/api/stripe/cancel")
async def stripe_cancel(request: Request):
    """El usuario cancelo el pago en Stripe. No hay nada que procesar."""
    return JSONResponse({"ok": True})


# ── Historial de pagos (API) ──────────────────────────────────
@router.get("/api/pagos/historial")
async def api_pagos_historial(request: Request):
    """Obtiene el historial de pagos del usuario"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    from core.stripe import obtener_pagos_stripe_usuario
    pagos_stripe = obtener_pagos_stripe_usuario(user["id"], limit=20)

    return JSONResponse({"ok": True, "pagos": pagos_stripe})
