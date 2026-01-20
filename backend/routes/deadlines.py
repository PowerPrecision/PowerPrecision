import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from database import db
from models.auth import UserRole
from models.deadline import DeadlineCreate, DeadlineUpdate, DeadlineResponse
from services.auth import get_current_user, require_roles
from services.email import send_email_notification
from services.history import log_history


router = APIRouter(prefix="/deadlines", tags=["Deadlines"])


@router.post("", response_model=DeadlineResponse)
async def create_deadline(data: DeadlineCreate, user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.CLIENTE:
        raise HTTPException(status_code=403, detail="Clientes não podem criar prazos")
    
    process = await db.processes.find_one({"id": data.process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    deadline_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    deadline_doc = {
        "id": deadline_id,
        "process_id": data.process_id,
        "title": data.title,
        "description": data.description,
        "due_date": data.due_date,
        "priority": data.priority,
        "completed": False,
        "created_by": user["id"],
        "created_at": now
    }
    
    await db.deadlines.insert_one(deadline_doc)
    await log_history(data.process_id, user, "Criou prazo", "deadline", None, data.title)
    
    await send_email_notification(
        process["client_email"],
        f"Novo Prazo: {data.title}",
        f"Foi adicionado um novo prazo ao seu processo: {data.title} - Data limite: {data.due_date}"
    )
    
    return DeadlineResponse(**{k: v for k, v in deadline_doc.items() if k != "_id"})


@router.get("", response_model=List[DeadlineResponse])
async def get_deadlines(process_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    
    if process_id:
        query["process_id"] = process_id
    elif user["role"] == UserRole.CLIENTE:
        processes = await db.processes.find({"client_id": user["id"]}, {"id": 1, "_id": 0}).to_list(1000)
        process_ids = [p["id"] for p in processes]
        query["process_id"] = {"$in": process_ids}
    
    deadlines = await db.deadlines.find(query, {"_id": 0}).to_list(1000)
    return [DeadlineResponse(**d) for d in deadlines]


@router.put("/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(deadline_id: str, data: DeadlineUpdate, user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.CLIENTE:
        raise HTTPException(status_code=403, detail="Clientes não podem editar prazos")
    
    deadline = await db.deadlines.find_one({"id": deadline_id}, {"_id": 0})
    if not deadline:
        raise HTTPException(status_code=404, detail="Prazo não encontrado")
    
    update_data = {}
    if data.title is not None:
        update_data["title"] = data.title
    if data.description is not None:
        update_data["description"] = data.description
    if data.due_date is not None:
        update_data["due_date"] = data.due_date
    if data.priority is not None:
        update_data["priority"] = data.priority
    if data.completed is not None:
        update_data["completed"] = data.completed
        if data.completed:
            await log_history(deadline["process_id"], user, "Concluiu prazo", "deadline", deadline["title"], "concluído")
    
    if update_data:
        await db.deadlines.update_one({"id": deadline_id}, {"$set": update_data})
    
    updated = await db.deadlines.find_one({"id": deadline_id}, {"_id": 0})
    return DeadlineResponse(**updated)


@router.delete("/{deadline_id}")
async def delete_deadline(deadline_id: str, user: dict = Depends(require_roles([UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.ADMIN]))):
    result = await db.deadlines.delete_one({"id": deadline_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Prazo não encontrado")
    return {"message": "Prazo eliminado"}
