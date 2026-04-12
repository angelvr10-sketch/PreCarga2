"""routers/payments.py - Endpoints de pago con MercadoPago y Stripe"""
import os
from fastapi import APIRouter, Request, Form, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from templates_cfg import templates

from core.auth import get_current_user, require_login
from core.payments import (
    crear_preferencia, procesar_notificacion_webhook, verificar_configuracion,
    obtener_pagos_usuario, obtener_ultimo_pago, obtener_pago_mercadopago,
    MP_PUBLIC_KEY, PLAN_PRICE, PLAN_DAYS, PLAN_CURRENCY
)
from core.stripe import (
    crear_checkout_session, procesar_webhook_stripe, procesar_evento_pago,
    obtener_info_sesion, verificar_configuracion_stripe, init_stripe_payments_db,
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
        "plan_precio": PLAN_PRICE,
        "plan_dias": PLAN_DAYS,
        "plan_moneda": PLAN_CURRENCY,
    })


# ── Checkout Page ──────────────────────────────────────────────
@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    redir = require_login(request)
    if redir:
        return redir

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Verificar config
    configurado = verificar_configuracion()
    stripe_configurado = verificar_configuracion_stripe()

    # Verificar si tiene pago pendiente
    ultimo_pago = obtener_ultimo_pago(user["id"])
    pago_pendiente = ultimo_pago if ultimo_pago and ultimo_pago["estado"] == "pending" else None

    return templates.TemplateResponse(request, "checkout.html", {
        "user": user,
        "mp_public_key": MP_PUBLIC_KEY if configurado else None,
        "configurado": configurado,
        "stripe_public_key": STRIPE_PUBLISHABLE_KEY if stripe_configurado else None,
        "stripe_configurado": stripe_configurado,
        "plan_precio": PLAN_PRICE,
        "plan_dias": PLAN_DAYS,
        "plan_moneda": PLAN_CURRENCY,
        "stripe_price": STRIPE_PRICE / 100,
        "stripe_currency": STRIPE_CURRENCY.upper(),
        "pago_pendiente": pago_pendiente,
    })


# ── Crear Preferencia AJAX ────────────────────────────────────
@router.post("/checkout/create")
async def checkout_create(request: Request):
    redir = require_login(request)
    if redir:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    print(f"DEBUG: Configurado={verificar_configuracion()}, MP_KEY={MP_PUBLIC_KEY[:20] if MP_PUBLIC_KEY else 'None'}...")

    if not verificar_configuracion():
        return JSONResponse({"ok": False, "error": "MercadoPago no configurado. Verifica el archivo .env"})

    try:
        print(f"DEBUG: Creando preferencia para usuario {user['id']} - {user['username']}")
        result = crear_preferencia(user["id"], user["username"])
        print(f"DEBUG: Preferencia creada OK: {result.get('id')}")
        return JSONResponse({
            "ok": True,
            "preference_id": result["id"],
            "init_point": result.get("init_point"),
            "sandbox_init_point": result.get("sandbox_init_point"),
        })
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"DEBUG: Error creando preferencia: {error_detail}")
        return JSONResponse({"ok": False, "error": str(e), "detail": error_detail})


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


# ── Webhook MercadoPago ──────────────────────────────────────
@router.post("/webhook/mercadopago")
async def webhook_mercadopago(request: Request):
    """Webhook para notificaciones de MercadoPago

    Este endpoint es publico - MercadoPago lo llama directamente.
    Debe estar en HTTPS para produccion.
    """
    try:
        body = await request.json()
        print(f"Webhook recibido: {body}")  # Log para debugging

        resultado = procesar_notificacion_webhook(body)

        if resultado:
            return JSONResponse({"status": "ok"}, status_code=200)
        else:
            # MercadoPago reintentara si devolvemos error
            return JSONResponse({"status": "error"}, status_code=500)

    except Exception as e:
        print(f"Error en webhook: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


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
        payment_info = obtener_info_sesion(session_id)
        if payment_info and payment_info.get("payment_status") == "paid":
            approved = True
            # Procesar el pago si no se ha procesado via webhook
            try:
                event = {"type": "checkout.session.completed", "data": {"object": payment_info}}
                procesar_evento_pago(event)
            except Exception as e:
                print(f"Error procesando pago en success: {e}")

    return templates.TemplateResponse(request, "stripe_success.html", {
        "user": user,
        "session_id": session_id,
        "payment_info": payment_info,
        "approved": approved,
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


# ── Success Page ──────────────────────────────────────────────
@router.get("/checkout/success", response_class=HTMLResponse)
async def checkout_success(request: Request,
                          payment_id: str = None,
                          preference_id: str = None,
                          external_reference: str = None):
    redir = require_login(request)
    if redir:
        return redir

    user = get_current_user(request)

    # Verificar estado del pago
    payment_status = None
    procesado = False

    if payment_id:
        try:
            payment_info = obtener_pago_mercadopago(payment_id)
            payment_status = payment_info.get("status")

            if payment_status == "approved":
                # Procesar el pago para activar suscripcion
                from core.payments import procesar_pago
                procesado = procesar_pago(payment_id)

        except Exception as e:
            print(f"Error verificando pago: {e}")

    return templates.TemplateResponse(request, "checkout_success.html", {
        "user": user,
        "payment_id": payment_id,
        "payment_status": payment_status,
        "procesado": procesado,
    })


# ── Pending Page ──────────────────────────────────────────────
@router.get("/checkout/pending", response_class=HTMLResponse)
async def checkout_pending(request: Request,
                           payment_id: str = None,
                           preference_id: str = None):
    redir = require_login(request)
    if redir:
        return redir

    user = get_current_user(request)

    return templates.TemplateResponse(request, "checkout_pending.html", {
        "user": user,
        "payment_id": payment_id,
        "preference_id": preference_id,
    })


# ── Failure Page ──────────────────────────────────────────────
@router.get("/checkout/failure", response_class=HTMLResponse)
async def checkout_failure(request: Request,
                           payment_id: str = None,
                           preference_id: str = None):
    redir = require_login(request)
    if redir:
        return redir

    user = get_current_user(request)

    # Informacion del pago fallido
    razon = "Pago rechazado o cancelado"

    return templates.TemplateResponse(request, "checkout_failure.html", {
        "user": user,
        "payment_id": payment_id,
        "razon": razon,
    })


# ── Historial de pagos (API) ──────────────────────────────────
@router.get("/api/pagos/historial")
async def api_pagos_historial(request: Request):
    redir = require_login(request)
    if redir:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    user = get_current_user(request)

    # Obtener pagos de ambos proveedores
    pagos_mp = obtener_pagos_usuario(user["id"], limit=20)
    pagos_stripe = []
    if verificar_configuracion_stripe():
        pagos_stripe = [
            {**p, "proveedor": "stripe"}
            for p in obtener_pagos_stripe_usuario(user["id"], limit=20)
        ]

    # Combinar y ordenar por fecha
    todos_pagos = [
        {**p, "proveedor": "mercadopago"}
        for p in pagos_mp
    ] + pagos_stripe
    todos_pagos.sort(key=lambda x: x.get("creado", ""), reverse=True)

    return JSONResponse({"ok": True, "pagos": todos_pagos[:20]})
