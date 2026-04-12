import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import uuid
from datetime import datetime, timezone, timedelta

db = None

def set_db(database):
    global db
    db = database

def send_verification_email(to_email, confirm_url, change_description):
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD')
    if not gmail_user or not gmail_password:
        raise Exception("Gmail credentials not configured")

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Proyecto Residente - Confirmar cambio de cuenta'
    msg['From'] = gmail_user
    msg['To'] = to_email

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h2 style="color: #000;">Proyecto Residente</h2>
            <p style="color: #666;">Confirmacion de cambio de cuenta</p>
        </div>
        <div style="background: #f9f9f9; border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <p style="font-size: 16px; color: #333;">Se ha solicitado el siguiente cambio:</p>
            <p style="font-size: 18px; font-weight: bold; color: #000;">{change_description}</p>
        </div>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{confirm_url}" 
               style="background: #000; color: #fff; padding: 14px 40px; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold;">
                Confirmar Cambio
            </a>
        </div>
        <p style="color: #999; font-size: 12px; text-align: center;">
            Si no solicitaste este cambio, ignora este correo. El enlace expira en 30 minutos.
        </p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to_email, msg.as_string())


async def create_change_request(change_type, new_value, admin_user_id):
    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    request_doc = {
        "token": token,
        "change_type": change_type,
        "new_value": new_value,
        "admin_user_id": admin_user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat(),
        "used": False
    }
    await db.admin_change_requests.insert_one(request_doc)
    return token


async def confirm_change(token):
    request = await db.admin_change_requests.find_one({"token": token, "used": False})
    if not request:
        return None, "Enlace invalido o ya utilizado"

    expires_at = datetime.fromisoformat(request["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        return None, "El enlace ha expirado"

    change_type = request["change_type"]
    new_value = request["new_value"]
    admin_user_id = request["admin_user_id"]

    if change_type == "name":
        await db.users.update_one(
            {"id": admin_user_id},
            {"$set": {"full_name": new_value}}
        )
    elif change_type == "password":
        import hashlib
        hashed = hashlib.sha256(new_value.encode()).hexdigest()
        await db.users.update_one(
            {"id": admin_user_id},
            {"$set": {"hashed_password": hashed}}
        )

    await db.admin_change_requests.update_one(
        {"token": token},
        {"$set": {"used": True}}
    )
    return change_type, None
