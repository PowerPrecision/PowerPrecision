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
    """
    Criar um novo evento/prazo no calendário.
    
    - Todos os utilizadores (exceto clientes) podem criar eventos
    - O evento é sempre atribuído ao próprio utilizador
    - Pode também ser atribuído a outros utilizadores (lista)
    """
    if user["role"] == UserRole.CLIENTE:
        raise HTTPException(status_code=403, detail="Clientes não podem criar prazos")
    
    process = None
    if data.process_id:
        process = await db.processes.find_one({"id": data.process_id}, {"_id": 0})
        if not process:
            raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    deadline_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Lista de utilizadores atribuídos - inclui sempre o criador
    assigned_users = data.assigned_user_ids or []
    if user["id"] not in assigned_users:
        assigned_users.append(user["id"])
    
    deadline_doc = {
        "id": deadline_id,
        "process_id": data.process_id,
        "title": data.title,
        "description": data.description,
        "due_date": data.due_date,
        "priority": data.priority,
        "completed": False,
        "created_by": user["id"],
        "created_at": now,
        "assigned_user_ids": assigned_users,
        # Campos legacy para compatibilidade
        "assigned_consultor_id": data.assigned_consultor_id,
        "assigned_mediador_id": data.assigned_mediador_id
    }
    
    await db.deadlines.insert_one(deadline_doc)
    
    if data.process_id:
        await log_history(data.process_id, user, "Criou prazo", "deadline", None, data.title)
    
    # Notificar todos os utilizadores atribuídos (exceto o criador)
    for assigned_id in assigned_users:
        if assigned_id != user["id"]:
            assigned_user = await db.users.find_one({"id": assigned_id}, {"_id": 0})
            if assigned_user:
                await send_email_notification(
                    assigned_user["email"],
                    f"Novo Prazo Atribuído: {data.title}",
                    f"Foi-lhe atribuído um novo prazo por {user['name']}:\n\n"
                    f"Título: {data.title}\n"
                    f"Data limite: {data.due_date}\n"
                    f"Prioridade: {data.priority}"
                )
    
    return DeadlineResponse(**{k: v for k, v in deadline_doc.items() if k != "_id"})


@router.get("", response_model=List[DeadlineResponse])
async def get_deadlines(process_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    """
    Obter prazos/eventos do utilizador.
    
    - Cada utilizador vê apenas os eventos onde está atribuído
    - Admin e CEO vêem todos os eventos
    """
    query = {}
    
    if process_id:
        query["process_id"] = process_id
    elif user["role"] == UserRole.CLIENTE:
        processes = await db.processes.find({"client_id": user["id"]}, {"id": 1, "_id": 0}).to_list(1000)
        process_ids = [p["id"] for p in processes]
        query["process_id"] = {"$in": process_ids}
    elif user["role"] in [UserRole.ADMIN, UserRole.CEO]:
        # Admin e CEO vêem todos
        pass
    else:
        # Outros utilizadores vêem eventos onde estão atribuídos
        query["$or"] = [
            {"assigned_user_ids": user["id"]},
            {"created_by": user["id"]},
            {"assigned_consultor_id": user["id"]},
            {"assigned_mediador_id": user["id"]}
        ]
    
    deadlines = await db.deadlines.find(query, {"_id": 0}).to_list(1000)
    return [DeadlineResponse(**d) for d in deadlines]


@router.get("/calendar")
async def get_calendar_deadlines(
    consultor_id: Optional[str] = None,
    mediador_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Obter eventos para o calendário.
    
    - Cada utilizador vê os seus próprios eventos
    - Admin pode filtrar por consultor/mediador
    """
    # Build deadline filter based on user role
    deadline_query = {}
    
    if user["role"] in [UserRole.ADMIN, UserRole.CEO]:
        # Admin/CEO podem filtrar ou ver todos
        if consultor_id:
            deadline_query["$or"] = [
                {"assigned_user_ids": consultor_id},
                {"assigned_consultor_id": consultor_id}
            ]
        elif mediador_id:
            deadline_query["$or"] = [
                {"assigned_user_ids": mediador_id},
                {"assigned_mediador_id": mediador_id}
            ]
    else:
        # Outros utilizadores vêem apenas os seus eventos
        deadline_query["$or"] = [
            {"assigned_user_ids": user["id"]},
            {"created_by": user["id"]},
            {"assigned_consultor_id": user["id"]},
            {"assigned_mediador_id": user["id"]}
        ]
    
    # Get deadlines
    deadlines = await db.deadlines.find(deadline_query, {"_id": 0}).to_list(1000)
    
    # Get all processes for reference
    processes = await db.processes.find({}, {"_id": 0}).to_list(1000)
    process_map = {p["id"]: p for p in processes}
    
    # Build deadline query
    # When no filters, get ALL deadlines
    if not consultor_id and not mediador_id:
        # No filters - get all deadlines
        deadline_query = {}
    else:
        # With filters - get deadlines from matching processes OR directly assigned
        or_conditions = []
        if process_ids:
            or_conditions.append({"process_id": {"$in": process_ids}})
        if consultor_id:
            or_conditions.append({"assigned_consultor_id": consultor_id})
        if mediador_id:
            or_conditions.append({"assigned_mediador_id": mediador_id})
        deadline_query = {"$or": or_conditions} if or_conditions else {}
    
    deadlines = await db.deadlines.find(deadline_query, {"_id": 0}).to_list(1000)
    
    # Enrich deadlines with process info
    result = []
    for d in deadlines:
        process = process_map.get(d.get("process_id"), {})
        if not process and d.get("process_id"):
            # Load process if not in map (might be filtered out)
            process = await db.processes.find_one({"id": d["process_id"]}, {"_id": 0}) or {}
        
        result.append({
            **d,
            "client_name": process.get("client_name", "Evento Geral"),
            "client_email": process.get("client_email", ""),
            "process_status": process.get("status", ""),
            "assigned_consultor_id": d.get("assigned_consultor_id") or process.get("assigned_consultor_id"),
            "assigned_mediador_id": d.get("assigned_mediador_id") or process.get("assigned_mediador_id"),
        })
    
    return result


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
        if data.completed and deadline.get("process_id"):
            await log_history(deadline["process_id"], user, "Concluiu prazo", "deadline", deadline["title"], "concluído")
    if data.assigned_consultor_id is not None:
        update_data["assigned_consultor_id"] = data.assigned_consultor_id
    if data.assigned_mediador_id is not None:
        update_data["assigned_mediador_id"] = data.assigned_mediador_id
    
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
