import uuid
from datetime import datetime, timezone
from fastapi import APIRouter

from database import db
from models.auth import UserRole
from models.process import PublicClientRegistration
from services.email import send_email_notification


router = APIRouter(prefix="/public", tags=["Public"])


@router.post("/client-registration")
async def public_client_registration(data: PublicClientRegistration):
    """Public endpoint for client registration - no authentication required"""
    
    existing_user = await db.users.find_one({"email": data.email})
    
    if existing_user:
        user_id = existing_user["id"]
        user_name = existing_user["name"]
    else:
        user_id = str(uuid.uuid4())
        user_name = data.name
        now = datetime.now(timezone.utc).isoformat()
        
        user_doc = {
            "id": user_id,
            "email": data.email,
            "password": None,
            "name": data.name,
            "phone": data.phone,
            "role": UserRole.CLIENTE,
            "is_active": True,
            "onedrive_folder": data.name,
            "created_at": now
        }
        await db.users.insert_one(user_doc)
    
    first_status = await db.workflow_statuses.find_one({}, {"_id": 0}, sort=[("order", 1)])
    initial_status = first_status["name"] if first_status else "pedido_inicial"
    
    process_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    process_doc = {
        "id": process_id,
        "client_id": user_id,
        "client_name": user_name,
        "client_email": data.email,
        "client_phone": data.phone,
        "process_type": data.process_type,
        "status": initial_status,
        "personal_data": data.personal_data.model_dump() if data.personal_data else None,
        "financial_data": data.financial_data.model_dump() if data.financial_data else None,
        "real_estate_data": None,
        "credit_data": None,
        "assigned_consultor_id": None,
        "assigned_mediador_id": None,
        "source": "public_form",
        "created_at": now,
        "updated_at": now
    }
    
    await db.processes.insert_one(process_doc)
    
    await db.history.insert_one({
        "id": str(uuid.uuid4()),
        "process_id": process_id,
        "user_id": user_id,
        "user_name": user_name,
        "action": "Cliente registou-se via formulário público",
        "field": None,
        "old_value": None,
        "new_value": None,
        "created_at": now
    })
    
    staff = await db.users.find({"role": {"$in": [UserRole.ADMIN, UserRole.CONSULTOR, UserRole.MEDIADOR]}}, {"_id": 0}).to_list(100)
    for member in staff:
        await send_email_notification(
            member["email"],
            f"Novo Registo de Cliente: {data.name}",
            f"Um novo cliente registou-se através do formulário público.\n\nNome: {data.name}\nEmail: {data.email}\nTelefone: {data.phone}\nTipo: {data.process_type}\n\nAceda ao sistema para dar seguimento ao processo."
        )
    
    return {
        "success": True,
        "message": "Registo criado com sucesso",
        "process_id": process_id
    }
