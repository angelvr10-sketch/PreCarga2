"""routers/payments.py - Endpoints de pago con Stripe"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from templates_cfg import templates

from core.auth import get_current_user, require_login
from core.stripe import (
    crear_checkout_session, procesar_webhook_stripe, procesar_evento_pago,
    obtener_info_sesion, verificar_configuracion_stripe,
    STRIPE_PUBLISHABLE_KEY, STRIPE_PRICE, STRIPE_DAYS, STRIPE_CURRENCY
)

router = APIRouter()


# ── Planes Page ───────────────────────────────────────────────
@router.get("/planes", response_class=HTMLResponse)
async def planes_page(request: Request):
    """Página de selección de planes - redirige al checkout"""
    redir = require_login(request)
    if redir:
        return redir

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(request, "planes.html", {
        "user": user,
        "plan_precio": STRIPE_PRICE / 100,
        "plan_dias": STRIPE_DAYS,
        "plan_moneda": STRIPE_CURRENCY.upper(),
    })


# ── Checkout Page ──────────────────────────────────────────────
@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Página de checkout con Stripe"""
    redir = require_login(request)
    if redir:
        return redir

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    stripe_configurado = verificar_configuracion_stripe()

    return templates.TemplateResponse(request, "checkout.html", {
        "user": user,
        "stripe_public_key": STRIPE_PUBLISHABLE_KEY if stripe_configurado else None,
        "stripe_configurado": stripe_configurado,
        "plan_precio": STRIPE_PRICE / 100,
        "plan_dias": STRIPE_DAYS,
        "plan_moneda": STRIPE_CURRENCY.upper(),
    })


# ── Crear Stripe Checkout Session AJAX ────────────────────────
@router.post("/checkout/stripe/create")
async def checkout_stripe_create(request: Request):
    """Crea una sesion de checkout con Stripe"""
    redir = require_login(request)
    if redir:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

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


# ── Stripe Checkout Page ─────────────────────────────────────
@router.get("/checkout/stripe", response_class=HTMLResponse)
async def stripe_checkout_page(request: Request):
    """Pagina de checkout con Stripe"""
    redir = require_login(request)
    if redir:
        return redir

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    stripe_configurado = verificar_configuracion_stripe()

    return templates.TemplateResponse(request, "stripe_checkout.html", {
        "user": user,
        "stripe_configurado": stripe_configurado,
        "stripe_price": STRIPE_PRICE / 100,
        "stripe_currency": STRIPE_CURRENCY.upper(),
    })


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


# ── Stripe Success Page ──────────────────────────────────────
@router.get("/stripe/success", response_class=HTMLResponse)
async def stripe_success(request: Request, session_id: str = None):
    """Pagina de exito despues de pago con Stripe"""
    redir = require_login(request)
    if redir:
        return redir

    user = get_current_user(request)
    payment_info = None
    approved = False

    if session_id:
        try:
            payment_info = obtener_info_sesion(session_id)
            print(f"DEBUG success: payment_info = {payment_info}")

            if payment_info and payment_info.get("payment_status") in ("paid", "no_payment_required"):
                approved = True
                # Procesar el pago directamente (puede que el webhook no llegue en dev)
                event = {"type": "checkout.session.completed", "data": {"object": payment_info}}
                procesar_evento_pago(event)
                print(f"DEBUG success: Pago procesado para session {session_id}")

            elif payment_info and payment_info.get("payment_status") == "unpaid":
                # Aún no pagado, Stripe redirigió pero el pago está pendiente
                approved = False
                print(f"DEBUG success: Pago aún no confirmado, payment_status=unpaid")

            else:
                # No pudimos obtener info de Stripe, pero intentamos procesar
                # usando el registro que ya creamos en la DB
                print(f"DEBUG success: payment_status desconocido o info no disponible, intentando procesar")
                fake_info = {"id": session_id, "payment_status": "unknown", "amount_total": STRIPE_PRICE, "metadata": {}}
                event = {"type": "checkout.session.completed", "data": {"object": fake_info}}
                result = procesar_evento_pago(event)
                if result:
                    approved = True
                    print(f"DEBUG success: Pago procesado exitosamente desde DB fallback")
                else:
                    approved = False

        except Exception as e:
            import traceback
            print(f"Error procesando pago en success: {e}")
            print(traceback.format_exc())
            # Si hay un error, mostrar la info que tengamos
            approved = False

    return templates.TemplateResponse(request, "stripe_success.html", {
        "user": user,
        "session_id": session_id,
        "payment_info": payment_info,
        "approved": approved,
        "plan_dias": STRIPE_DAYS,
    })


# ── Stripe Cancel Page ───────────────────────────────────────
@router.get("/stripe/cancel", response_class=HTMLResponse)
async def stripe_cancel(request: Request):
    """Pagina de cancelacion de pago con Stripe"""
    redir = require_login(request)
    if redir:
        return redir

    user = get_current_user(request)

    return templates.TemplateResponse(request, "stripe_cancel.html", {
        "user": user,
    })


# ── Historial de pagos (API) ──────────────────────────────────
@router.get("/api/pagos/historial")
async def api_pagos_historial(request: Request):
    """Obtiene el historial de pagos del usuario"""
    redir = require_login(request)
    if redir:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    user = get_current_user(request)

    from core.stripe import obtener_pagos_stripe_usuario
    pagos_stripe = obtener_pagos_stripe_usuario(user["id"], limit=20)

    return JSONResponse({"ok": True, "pagos": pagos_stripe})
