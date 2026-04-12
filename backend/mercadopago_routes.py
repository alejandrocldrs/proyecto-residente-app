"""
MercadoPago payment integration routes.
Handles payment preference creation, webhook notifications, and payment status checks.
"""
import os
import uuid
import hmac
import hashlib
import mercadopago
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional

mp_router = APIRouter()

# Get DB reference - will be set by server.py
db = None
# Callback for post-payment activation email
_send_activation_callback = None

def set_db(database):
    global db
    db = database

def set_activation_callback(callback):
    global _send_activation_callback
    _send_activation_callback = callback

def get_mp_sdk():
    access_token = os.environ.get("MP_ACCESS_TOKEN", "")
    if not access_token:
        raise HTTPException(status_code=500, detail="MercadoPago not configured")
    return mercadopago.SDK(access_token)


async def get_current_price():
    """Get current subscription price from DB or default."""
    settings = await db.app_settings.find_one({"key": "subscription_price"}, {"_id": 0})
    if settings:
        return settings["value"]
    return 1500


class PaymentRequest(BaseModel):
    user_id: str


class PaymentStatusResponse(BaseModel):
    status: str
    payment_id: Optional[str] = None
    message: str


@mp_router.post("/payments/create-preference")
async def create_payment_preference(req: PaymentRequest):
    """Create a MercadoPago checkout preference for user subscription."""
    user = await db.users.find_one({"id": req.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.get("payment_status") == "completed":
        raise HTTPException(status_code=400, detail="El usuario ya ha completado el pago")

    sdk = get_mp_sdk()
    app_url = os.environ.get("APP_URL", "")
    frontend_url = os.environ.get("FRONTEND_URL", app_url)
    current_price = await get_current_price()

    preference_data = {
        "items": [
            {
                "id": f"sub_{req.user_id}",
                "title": "Proyecto Residente - 6 meses de acceso",
                "description": "Acceso completo a la plataforma de preparación ENARM por 6 meses",
                "quantity": 1,
                "unit_price": current_price,
                "currency_id": "MXN"
            }
        ],
        "payer": {
            "email": user.get("email", ""),
        },
        "back_urls": {
            "success": f"{frontend_url}/payment-result?status=success&user_id={req.user_id}",
            "failure": f"{frontend_url}/payment-result?status=failure&user_id={req.user_id}",
            "pending": f"{frontend_url}/payment-result?status=pending&user_id={req.user_id}",
        },
        "auto_return": "approved",
        "external_reference": req.user_id,
        "notification_url": f"{app_url}/api/payments/webhook",
        "binary_mode": True,
    }

    try:
        result = sdk.preference().create(preference_data)
        if result["status"] == 201:
            response = result["response"]
            # Store preference ID on user
            await db.users.update_one(
                {"id": req.user_id},
                {"$set": {"mp_preference_id": response["id"]}}
            )
            return {
                "preference_id": response["id"],
                "init_point": response["init_point"],
                "sandbox_init_point": response.get("sandbox_init_point", ""),
            }
        else:
            raise HTTPException(status_code=400, detail="Error al crear preferencia de pago")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de MercadoPago: {str(e)}")


@mp_router.post("/payments/webhook")
async def mercadopago_webhook(request: Request):
    """Handle MercadoPago webhook notifications with signature validation."""
    # Validate webhook signature
    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")
    
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored"}

    action = payload.get("action")
    data = payload.get("data", {})
    notification_type = payload.get("type")

    if notification_type != "payment":
        return {"status": "ignored"}

    payment_id = data.get("id")
    if not payment_id:
        return {"status": "ignored"}

    # Validate signature if secret key is configured
    mp_secret = os.environ.get("MP_ACCESS_TOKEN", "")
    if x_signature and mp_secret:
        try:
            parts = {}
            for part in x_signature.split(","):
                kv = part.strip().split("=", 1)
                if len(kv) == 2:
                    parts[kv[0].strip()] = kv[1].strip()
            ts = parts.get("ts", "")
            v1 = parts.get("v1", "")
            
            if ts and v1:
                manifest = f"id:{payment_id};request-id:{x_request_id};ts:{ts};"
                computed = hmac.new(mp_secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(computed, v1):
                    print(f"Webhook signature mismatch - proceeding with payment verification")
        except Exception as sig_err:
            print(f"Webhook signature validation error: {sig_err}")

    try:
        sdk = get_mp_sdk()
        payment_result = sdk.payment().get(int(payment_id))

        if payment_result["status"] != 200:
            return {"status": "error", "message": "Could not fetch payment"}

        payment_data = payment_result["response"]
        payment_status = payment_data.get("status")
        external_reference = payment_data.get("external_reference")

        if not external_reference:
            return {"status": "error", "message": "No external reference"}

        user = await db.users.find_one({"id": external_reference})
        if not user:
            return {"status": "error", "message": "User not found"}

        # Record payment
        payment_record = {
            "id": str(uuid.uuid4()),
            "user_id": external_reference,
            "mp_payment_id": str(payment_id),
            "amount": payment_data.get("transaction_amount", 1500),
            "currency": "MXN",
            "status": payment_status,
            "preference_id": user.get("mp_preference_id", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.payments.insert_one(payment_record)

        if payment_status == "approved":
            # Record payment as approved but DON'T auto-approve user
            # Instead, send activation email
            await db.users.update_one(
                {"id": external_reference},
                {
                    "$set": {
                        "payment_status": "completed",
                        "mp_payment_id": str(payment_id),
                    }
                }
            )
            # Send activation email
            if _send_activation_callback:
                try:
                    await _send_activation_callback(external_reference)
                except Exception as email_err:
                    print(f"Error sending activation email from webhook: {email_err}")
        elif payment_status == "rejected":
            await db.users.update_one(
                {"id": external_reference},
                {"$set": {"payment_status": "failed"}}
            )
        elif payment_status in ("pending", "in_process"):
            await db.users.update_one(
                {"id": external_reference},
                {"$set": {"payment_status": "pending"}}
            )

        return {"status": "ok", "payment_status": payment_status}

    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}


@mp_router.get("/payments/status/{user_id}")
async def get_payment_status(user_id: str):
    """Check the payment status for a user."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.get("account_type") == "paid":
        return {
            "status": "approved",
            "message": "Tu cuenta está activa. Puedes iniciar sesión."
        }

    payment_status = user.get("payment_status", "none")
    if payment_status == "completed":
        return {
            "status": "approved",
            "message": "Pago completado. Tu cuenta está activa."
        }
    elif payment_status == "pending":
        return {
            "status": "pending",
            "message": "Tu pago está siendo procesado. Te notificaremos cuando esté listo."
        }
    elif payment_status == "failed":
        return {
            "status": "failed",
            "message": "El pago fue rechazado. Intenta de nuevo."
        }
    else:
        return {
            "status": "none",
            "message": "No se ha realizado ningún pago."
        }


@mp_router.post("/payments/verify-and-approve/{user_id}")
async def verify_and_approve(user_id: str, payment_id: Optional[str] = Query(None)):
    """
    Called from frontend after MercadoPago redirect.
    Checks if the user has a completed payment via the back_url params
    and approves them if the webhook hasn't fired yet.
    """
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.get("account_type") == "paid":
        return {"status": "already_approved", "message": "Tu cuenta ya está activa."}

    # Check if there's a payment record from webhook
    payment = await db.payments.find_one(
        {"user_id": user_id, "status": "approved"},
        sort=[("created_at", -1)]
    )

    if payment:
        # Payment was already recorded by webhook - send activation email
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"payment_status": "completed"}}
        )
        if _send_activation_callback:
            try:
                await _send_activation_callback(user_id)
            except Exception as e:
                print(f"Error sending activation email: {e}")
        return {"status": "activation_sent", "message": "Pago verificado. Revisa tu correo para activar tu cuenta.", "user_id": user_id}

    # If payment_id was provided by MercadoPago redirect, verify it directly
    if payment_id:
        try:
            sdk = get_mp_sdk()
            payment_info = sdk.payment().get(int(payment_id))
            if payment_info["status"] == 200:
                p = payment_info["response"]
                if p.get("status") == "approved":
                    await db.users.update_one(
                        {"id": user_id},
                        {
                            "$set": {
                                "payment_status": "completed",
                                "mp_payment_id": str(payment_id),
                            }
                        }
                    )
                    # Save payment record
                    payment_record = {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "mp_payment_id": str(payment_id),
                        "amount": p.get("transaction_amount", 1500),
                        "currency": "MXN",
                        "status": "approved",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.payments.insert_one(payment_record)
                    # Send activation email
                    if _send_activation_callback:
                        try:
                            await _send_activation_callback(user_id)
                        except Exception as e:
                            print(f"Error sending activation email: {e}")
                    return {"status": "activation_sent", "message": "Pago verificado. Revisa tu correo para activar tu cuenta.", "user_id": user_id}
        except Exception as e:
            print(f"Direct payment verify error: {e}")

    # Fallback: search by external_reference
    preference_id = user.get("mp_preference_id")
    if preference_id:
        try:
            sdk = get_mp_sdk()
            filters = {"external_reference": user_id}
            result = sdk.payment().search(filters)
            if result["status"] == 200:
                payments = result["response"].get("results", [])
                for p in payments:
                    if p.get("status") == "approved":
                        await db.users.update_one(
                            {"id": user_id},
                            {
                                "$set": {
                                    "payment_status": "completed",
                                    "mp_payment_id": str(p.get("id")),
                                }
                            }
                        )
                        payment_record = {
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "mp_payment_id": str(p.get("id")),
                            "amount": p.get("transaction_amount", 1500),
                            "currency": "MXN",
                            "status": "approved",
                            "preference_id": preference_id,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                        await db.payments.insert_one(payment_record)
                        if _send_activation_callback:
                            try:
                                await _send_activation_callback(user_id)
                            except Exception as e:
                                print(f"Error sending activation email: {e}")
                        return {"status": "activation_sent", "message": "Pago verificado. Revisa tu correo para activar tu cuenta.", "user_id": user_id}
        except Exception as e:
            print(f"Verify error: {e}")

    return {
        "status": "pending",
        "message": "Estamos verificando tu pago. Esto puede tomar unos minutos."
    }
