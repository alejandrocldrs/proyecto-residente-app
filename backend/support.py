from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

support_router = APIRouter(prefix="/support", tags=["support"])

db = None

def set_db(database):
    global db
    db = database

class CreateTicketRequest(BaseModel):
    message: str
    category: Optional[str] = "general"

class ReplyRequest(BaseModel):
    message: str

def get_user_from_token(token: str):
    """This will be replaced by the actual auth dependency from server.py"""
    pass

# Will be set from server.py
get_current_user = None

def set_auth_dependency(dep):
    global get_current_user
    get_current_user = dep

@support_router.post("/create")
async def create_ticket(req: CreateTicketRequest, current_user: dict = Depends(lambda: None)):
    if get_current_user is None:
        raise HTTPException(status_code=500, detail="Auth not configured")
    pass

# The actual endpoints use a wrapper pattern since we need the auth dependency from server.py
# We'll define them as plain async functions and register them in server.py

async def create_ticket_handler(req_message: str, req_category: str, current_user: dict):
    ticket = {
        "ticket_id": str(uuid.uuid4()),
        "user_id": current_user["user_id"],
        "user_name": current_user.get("full_name", ""),
        "user_email": current_user.get("email", ""),
        "message": req_message,
        "category": req_category or "general",
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "replies": [],
        "admin_read": False,
        "user_has_unread": False
    }
    await db.support_tickets.insert_one(ticket)
    ticket.pop("_id", None)
    return ticket

async def get_my_tickets_handler(current_user: dict):
    tickets = await db.support_tickets.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    # Mark user unread as read when user fetches
    await db.support_tickets.update_many(
        {"user_id": current_user["user_id"], "user_has_unread": True},
        {"$set": {"user_has_unread": False}}
    )
    return tickets

async def get_all_tickets_handler():
    tickets = await db.support_tickets.find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return tickets

async def admin_reply_handler(ticket_id: str, message: str):
    reply = {
        "reply_id": str(uuid.uuid4()),
        "from_role": "admin",
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.support_tickets.update_one(
        {"ticket_id": ticket_id},
        {
            "$push": {"replies": reply},
            "$set": {"status": "replied", "admin_read": True, "user_has_unread": True}
        }
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {"ok": True}

async def user_reply_handler(ticket_id: str, message: str, current_user: dict):
    reply = {
        "reply_id": str(uuid.uuid4()),
        "from_role": "user",
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.support_tickets.update_one(
        {"ticket_id": ticket_id, "user_id": current_user["user_id"]},
        {
            "$push": {"replies": reply},
            "$set": {"status": "open", "admin_read": False}
        }
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {"ok": True}

async def get_unread_count_admin_handler():
    count = await db.support_tickets.count_documents({"admin_read": False})
    return {"count": count}

async def get_unread_count_user_handler(current_user: dict):
    count = await db.support_tickets.count_documents({
        "user_id": current_user["user_id"],
        "user_has_unread": True
    })
    return {"count": count}

async def mark_ticket_read_admin_handler(ticket_id: str):
    await db.support_tickets.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"admin_read": True}}
    )
    return {"ok": True}
