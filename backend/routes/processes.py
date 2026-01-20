import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from database import db
from models.auth import UserRole
from models.process import (
    ProcessType, ProcessCreate, ProcessUpdate, ProcessResponse
)
from services.auth import get_current_user, require_roles
from services.email import send_email_notification
from services.history import log_history, log_data_changes


router = APIRouter(prefix="/processes", tags=["Processes"])


@router.post("", response_model=ProcessResponse)
async def create_process(data: ProcessCreate, user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.CLIENTE:
        raise HTTPException(status_code=403, detail="Apenas clientes podem criar processos")
    
    first_status = await db.workflow_statuses.find_one({}, {"_id": 0}, sort=[("order", 1)])
    initial_status = first_status["name"] if first_status else "pedido_inicial"
    
    process_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    process_doc = {
        "id": process_id,
        "client_id": user["id"],
        "client_name": user["name"],
        "client_email": user["email"],
        "process_type": data.process_type,
        "status": initial_status,
        "personal_data": data.personal_data.model_dump() if data.personal_data else None,
        "financial_data": data.financial_data.model_dump() if data.financial_data else None,
        "real_estate_data": None,
        "credit_data": None,
        "assigned_consultor_id": None,
        "assigned_mediador_id": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.processes.insert_one(process_doc)
    await log_history(process_id, user, "Criou processo")
    
    admins = await db.users.find({"role": UserRole.ADMIN}, {"_id": 0}).to_list(100)
    for admin in admins:
        await send_email_notification(
            admin["email"],
            "Novo Processo Criado",
            f"O cliente {user['name']} criou um novo processo de {data.process_type}."
        )
    
    return ProcessResponse(**{k: v for k, v in process_doc.items() if k != "_id"})


@router.get("", response_model=List[ProcessResponse])
async def get_processes(user: dict = Depends(get_current_user)):
    query = {}
    
    if user["role"] == UserRole.CLIENTE:
        query["client_id"] = user["id"]
    elif user["role"] == UserRole.CONSULTOR:
        query["$or"] = [
            {"assigned_consultor_id": user["id"]},
            {"assigned_consultor_id": None, "process_type": {"$in": [ProcessType.IMOBILIARIA, ProcessType.AMBOS]}}
        ]
    elif user["role"] == UserRole.MEDIADOR:
        query["$or"] = [
            {"assigned_mediador_id": user["id"]},
            {"assigned_mediador_id": None, "process_type": {"$in": [ProcessType.CREDITO, ProcessType.AMBOS]}}
        ]
    
    processes = await db.processes.find(query, {"_id": 0}).to_list(1000)
    return [ProcessResponse(**p) for p in processes]


@router.get("/{process_id}", response_model=ProcessResponse)
async def get_process(process_id: str, user: dict = Depends(get_current_user)):
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    if user["role"] == UserRole.CLIENTE and process["client_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    return ProcessResponse(**process)


@router.put("/{process_id}", response_model=ProcessResponse)
async def update_process(process_id: str, data: ProcessUpdate, user: dict = Depends(get_current_user)):
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    valid_statuses = [s["name"] for s in await db.workflow_statuses.find({}, {"name": 1, "_id": 0}).to_list(100)]
    
    if user["role"] == UserRole.CLIENTE:
        if process["client_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Acesso negado")
        if data.personal_data:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        if data.financial_data:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
    
    elif user["role"] == UserRole.CONSULTOR:
        if data.personal_data:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        if data.financial_data:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
        if data.real_estate_data:
            await log_data_changes(process_id, user, process.get("real_estate_data"), data.real_estate_data.model_dump(), "dados imobiliários")
            update_data["real_estate_data"] = data.real_estate_data.model_dump()
        if data.status and (data.status in valid_statuses or not valid_statuses):
            await log_history(process_id, user, "Alterou estado", "status", process["status"], data.status)
            update_data["status"] = data.status
        if not process.get("assigned_consultor_id"):
            update_data["assigned_consultor_id"] = user["id"]
    
    elif user["role"] == UserRole.MEDIADOR:
        if data.personal_data:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        if data.financial_data:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
        if data.credit_data:
            credit_statuses = await db.workflow_statuses.find({"order": {"$gte": 3}}, {"name": 1, "_id": 0}).to_list(100)
            allowed_statuses = [s["name"] for s in credit_statuses] if credit_statuses else ["autorizacao_bancaria", "aprovado"]
            if process["status"] not in allowed_statuses:
                raise HTTPException(status_code=400, detail="Dados de crédito só podem ser adicionados após autorização bancária")
            await log_data_changes(process_id, user, process.get("credit_data"), data.credit_data.model_dump(), "dados de crédito")
            update_data["credit_data"] = data.credit_data.model_dump()
        if data.status and (data.status in valid_statuses or not valid_statuses):
            await log_history(process_id, user, "Alterou estado", "status", process["status"], data.status)
            update_data["status"] = data.status
            await send_email_notification(
                process["client_email"],
                f"Estado do Processo Atualizado",
                f"O estado do seu processo foi atualizado para: {data.status}"
            )
        if not process.get("assigned_mediador_id"):
            update_data["assigned_mediador_id"] = user["id"]
    
    elif user["role"] == UserRole.ADMIN:
        if data.personal_data:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        if data.financial_data:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
        if data.real_estate_data:
            await log_data_changes(process_id, user, process.get("real_estate_data"), data.real_estate_data.model_dump(), "dados imobiliários")
            update_data["real_estate_data"] = data.real_estate_data.model_dump()
        if data.credit_data:
            await log_data_changes(process_id, user, process.get("credit_data"), data.credit_data.model_dump(), "dados de crédito")
            update_data["credit_data"] = data.credit_data.model_dump()
        if data.status:
            await log_history(process_id, user, "Alterou estado", "status", process["status"], data.status)
            update_data["status"] = data.status
    
    await db.processes.update_one({"id": process_id}, {"$set": update_data})
    updated = await db.processes.find_one({"id": process_id}, {"_id": 0})
    
    return ProcessResponse(**updated)


@router.post("/{process_id}/assign")
async def assign_process(
    process_id: str, 
    consultor_id: Optional[str] = None,
    mediador_id: Optional[str] = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    process = await db.processes.find_one({"id": process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if consultor_id:
        consultor = await db.users.find_one({"id": consultor_id, "role": UserRole.CONSULTOR})
        if not consultor:
            raise HTTPException(status_code=404, detail="Consultor não encontrado")
        update_data["assigned_consultor_id"] = consultor_id
        await log_history(process_id, user, "Atribuiu consultor", "assigned_consultor_id", None, consultor["name"])
    
    if mediador_id:
        mediador = await db.users.find_one({"id": mediador_id, "role": UserRole.MEDIADOR})
        if not mediador:
            raise HTTPException(status_code=404, detail="Mediador não encontrado")
        update_data["assigned_mediador_id"] = mediador_id
        await log_history(process_id, user, "Atribuiu mediador", "assigned_mediador_id", None, mediador["name"])
    
    await db.processes.update_one({"id": process_id}, {"$set": update_data})
    return {"message": "Processo atribuído com sucesso"}
