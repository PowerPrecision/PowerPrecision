import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from database import db
from models.auth import UserRole, UserCreate, UserUpdate, UserResponse
from models.workflow import WorkflowStatusCreate, WorkflowStatusUpdate, WorkflowStatusResponse
from services.auth import hash_password, require_roles


router = APIRouter(prefix="/admin", tags=["Admin"])


# ============== WORKFLOW STATUS ROUTES ==============

@router.get("/workflow-statuses", response_model=List[WorkflowStatusResponse])
async def get_workflow_statuses(user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CONSULTOR, UserRole.MEDIADOR]))):
    """Get all workflow statuses ordered by order field"""
    statuses = await db.workflow_statuses.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return [WorkflowStatusResponse(**s) for s in statuses]


@router.post("/workflow-statuses", response_model=WorkflowStatusResponse)
async def create_workflow_status(data: WorkflowStatusCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a new workflow status"""
    existing = await db.workflow_statuses.find_one({"name": data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Estado já existe")
    
    status_doc = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "label": data.label,
        "order": data.order,
        "color": data.color,
        "description": data.description,
        "is_default": False
    }
    
    await db.workflow_statuses.insert_one(status_doc)
    return WorkflowStatusResponse(**{k: v for k, v in status_doc.items() if k != "_id"})


@router.put("/workflow-statuses/{status_id}", response_model=WorkflowStatusResponse)
async def update_workflow_status(status_id: str, data: WorkflowStatusUpdate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Update a workflow status"""
    status = await db.workflow_statuses.find_one({"id": status_id}, {"_id": 0})
    if not status:
        raise HTTPException(status_code=404, detail="Estado não encontrado")
    
    update_data = {}
    if data.label is not None:
        update_data["label"] = data.label
    if data.order is not None:
        update_data["order"] = data.order
    if data.color is not None:
        update_data["color"] = data.color
    if data.description is not None:
        update_data["description"] = data.description
    
    if update_data:
        await db.workflow_statuses.update_one({"id": status_id}, {"$set": update_data})
    
    updated = await db.workflow_statuses.find_one({"id": status_id}, {"_id": 0})
    return WorkflowStatusResponse(**updated)


@router.delete("/workflow-statuses/{status_id}")
async def delete_workflow_status(status_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Delete a workflow status"""
    status = await db.workflow_statuses.find_one({"id": status_id})
    if not status:
        raise HTTPException(status_code=404, detail="Estado não encontrado")
    
    if status.get("is_default"):
        raise HTTPException(status_code=400, detail="Não pode eliminar estados padrão")
    
    process_count = await db.processes.count_documents({"status": status["name"]})
    if process_count > 0:
        raise HTTPException(status_code=400, detail=f"Existem {process_count} processos com este estado")
    
    await db.workflow_statuses.delete_one({"id": status_id})
    return {"message": "Estado eliminado"}


# ============== USER MANAGEMENT ROUTES ==============

@router.get("/users", response_model=List[UserResponse])
async def get_users(role: Optional[str] = None, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    query = {}
    if role:
        query["role"] = role
    
    users = await db.users.find(query, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]


@router.post("/users", response_model=UserResponse)
async def create_user(data: UserCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já registado")
    
    if data.role not in [UserRole.CLIENTE, UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.INTERMEDIARIO, UserRole.DIRETOR, UserRole.ADMINISTRATIVO, UserRole.CEO, UserRole.ADMIN]:
        raise HTTPException(status_code=400, detail="Role inválido")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password": hash_password(data.password),
        "name": data.name,
        "phone": data.phone,
        "role": data.role,
        "is_active": True,
        "onedrive_folder": data.onedrive_folder or data.name,
        "created_at": now
    }
    
    await db.users.insert_one(user_doc)
    
    return UserResponse(
        id=user_id,
        email=data.email,
        name=data.name,
        phone=data.phone,
        role=data.role,
        created_at=now,
        onedrive_folder=data.onedrive_folder or data.name
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, data: UserUpdate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.phone is not None:
        update_data["phone"] = data.phone
    if data.role is not None:
        if data.role not in [UserRole.CLIENTE, UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.INTERMEDIARIO, UserRole.DIRETOR, UserRole.ADMINISTRATIVO, UserRole.CEO, UserRole.ADMIN]:
            raise HTTPException(status_code=400, detail="Role inválido")
        update_data["role"] = data.role
    if data.is_active is not None:
        update_data["is_active"] = data.is_active
    if data.onedrive_folder is not None:
        update_data["onedrive_folder"] = data.onedrive_folder
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return UserResponse(**updated)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Não pode eliminar a própria conta")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    return {"message": "Utilizador eliminado"}


# ============== IMPERSONATE (VER COMO OUTRO UTILIZADOR) ==============

@router.post("/impersonate/{user_id}")
async def impersonate_user(user_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """
    Permite ao admin ver o sistema como outro utilizador.
    Gera um token temporário com os dados do utilizador alvo.
    
    O token inclui informação sobre o admin original para auditoria.
    """
    from services.auth import create_access_token
    
    # Verificar que o utilizador alvo existe
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    
    # Não permitir impersonate de outro admin
    if target_user["role"] == UserRole.ADMIN and user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Não pode personificar outro administrador")
    
    # Criar token com dados do utilizador alvo, mas marcar como impersonated
    token_data = {
        "sub": target_user["id"],
        "email": target_user["email"],
        "role": target_user["role"],
        "name": target_user["name"],
        # Informação de auditoria
        "impersonated_by": user["id"],
        "impersonated_by_name": user["name"],
        "is_impersonated": True
    }
    
    access_token = create_access_token(token_data)
    
    # Log da acção
    await db.history.insert_one({
        "id": str(uuid.uuid4()),
        "process_id": None,
        "user_id": user["id"],
        "user_name": user["name"],
        "action": f"Admin impersonou utilizador: {target_user['name']} ({target_user['email']})",
        "field": "impersonate",
        "old_value": None,
        "new_value": target_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": target_user["id"],
            "email": target_user["email"],
            "name": target_user["name"],
            "role": target_user["role"],
            "is_impersonated": True,
            "impersonated_by": user["name"]
        }
    }


@router.post("/stop-impersonate")
async def stop_impersonate(user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO, UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.DIRETOR, UserRole.ADMINISTRATIVO]))):
    """
    Terminar sessão de impersonate e voltar à conta original.
    Requer o token do admin original.
    """
    from services.auth import create_access_token
    
    if not user.get("impersonated_by"):
        raise HTTPException(status_code=400, detail="Não está em modo de personificação")
    
    # Buscar o admin original
    admin_user = await db.users.find_one({"id": user["impersonated_by"]}, {"_id": 0, "password": 0})
    if not admin_user:
        raise HTTPException(status_code=404, detail="Administrador original não encontrado")
    
    # Criar novo token para o admin
    token_data = {
        "sub": admin_user["id"],
        "email": admin_user["email"],
        "role": admin_user["role"],
        "name": admin_user["name"]
    }
    
    access_token = create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": admin_user["id"],
            "email": admin_user["email"],
            "name": admin_user["name"],
            "role": admin_user["role"]
        }
    }


# ============== PROCESS NUMBER MIGRATION ==============

@router.post("/migrate-process-numbers")
async def migrate_process_numbers(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """
    Atribuir números sequenciais a todos os processos que não têm.
    Os processos são ordenados por data de criação (mais antigos primeiro).
    """
    # Buscar processos sem número, ordenados por data de criação
    processes_without_number = await db.processes.find(
        {"$or": [{"process_number": {"$exists": False}}, {"process_number": None}]},
        {"_id": 0, "id": 1, "created_at": 1, "client_name": 1}
    ).sort("created_at", 1).to_list(10000)
    
    if not processes_without_number:
        return {"message": "Todos os processos já têm número atribuído", "updated": 0}
    
    # Obter o maior número existente
    max_result = await db.processes.find_one(
        {"process_number": {"$exists": True, "$ne": None}},
        {"process_number": 1},
        sort=[("process_number", -1)]
    )
    
    next_number = (max_result["process_number"] + 1) if max_result and max_result.get("process_number") else 1
    
    updated_count = 0
    for process in processes_without_number:
        await db.processes.update_one(
            {"id": process["id"]},
            {"$set": {"process_number": next_number}}
        )
        next_number += 1
        updated_count += 1
    
    return {
        "message": f"Números atribuídos a {updated_count} processos",
        "updated": updated_count,
        "first_number": next_number - updated_count,
        "last_number": next_number - 1
    }


