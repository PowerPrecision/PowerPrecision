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
    
    # Cliente não é um utilizador do sistema - é um processo
    if data.role == UserRole.CLIENTE:
        raise HTTPException(status_code=400, detail="Cliente não pode ser criado como utilizador. O cliente é representado pelo processo.")
    
    if data.role not in [UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.INTERMEDIARIO, UserRole.DIRETOR, UserRole.ADMINISTRATIVO, UserRole.CEO, UserRole.ADMIN]:
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
    
    # Associar automaticamente processos do Trello que têm este utilizador atribuído
    # Verifica se o nome do utilizador corresponde a algum membro atribuído no Trello
    name_lower = data.name.lower()
    name_parts = [p for p in name_lower.split() if len(p) >= 3]
    
    # Procurar processos com trello_members que corresponda ao nome
    query = {"trello_members": {"$exists": True, "$ne": []}}
    processes_to_update = await db.processes.find(query, {"_id": 0, "id": 1, "trello_members": 1}).to_list(1000)
    
    updated_count = 0
    for proc in processes_to_update:
        members = proc.get("trello_members", [])
        # Verificar se o nome do utilizador está na lista de membros
        for member in members:
            member_lower = member.lower()
            # Verificar se alguma parte do nome corresponde
            if any(part in member_lower for part in name_parts):
                # Determinar qual campo atualizar baseado no role
                if data.role in [UserRole.CONSULTOR]:
                    await db.processes.update_one(
                        {"id": proc["id"]},
                        {"$set": {"assigned_consultor_id": user_id}}
                    )
                    updated_count += 1
                elif data.role in [UserRole.MEDIADOR, UserRole.INTERMEDIARIO]:
                    await db.processes.update_one(
                        {"id": proc["id"]},
                        {"$set": {"assigned_mediador_id": user_id}}
                    )
                    updated_count += 1
                break  # Já encontrou match, passar ao próximo processo
    
    if updated_count > 0:
        import logging
        logging.getLogger(__name__).info(f"Utilizador {data.name} criado e associado a {updated_count} processos automaticamente")
    
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
        # Proteger admin de ser desactivado
        target_user = await db.users.find_one({"id": user_id})
        if target_user and target_user.get("role") == "admin" and data.is_active == False:
            raise HTTPException(status_code=400, detail="Não é possível desactivar o utilizador administrador")
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




# ============== AI CONFIGURATION ROUTES (Admin Only) ==============

@router.get("/ai-config")
async def get_ai_configuration(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """
    Obtém a configuração actual de IA.
    
    Retorna qual modelo é usado para cada tarefa:
    - scraper_extraction: Extração de dados de páginas web
    - document_analysis: Análise de documentos
    - weekly_report: Relatório semanal de erros
    - error_analysis: Análise de erros
    """
    from config import AI_MODELS, AI_CONFIG_DEFAULTS, GEMINI_API_KEY, EMERGENT_LLM_KEY
    from services.ai_page_analyzer import get_ai_config
    
    current_config = await get_ai_config()
    
    # Verificar quais chaves estão configuradas
    available_providers = []
    if GEMINI_API_KEY:
        available_providers.append("gemini")
    if EMERGENT_LLM_KEY:
        available_providers.append("openai")
    
    # Obter modelos da DB (se existirem) ou usar config padrão
    db_models = await db.ai_models.find({}, {"_id": 0}).to_list(100)
    if db_models:
        available_models = {m["key"]: m for m in db_models if m.get("provider") in available_providers}
    else:
        # Fallback para config hardcoded (migração)
        available_models = {}
        for model_key, model_info in AI_MODELS.items():
            if model_info["provider"] in available_providers:
                available_models[model_key] = model_info
    
    # Obter tarefas da DB (se existirem) ou usar defaults
    db_tasks = await db.ai_tasks.find({}, {"_id": 0}).to_list(100)
    if db_tasks:
        task_descriptions = {t["key"]: t["description"] for t in db_tasks}
        task_defaults = {t["key"]: t.get("default_model") for t in db_tasks}
    else:
        task_descriptions = {
            "scraper_extraction": "Extração de dados de páginas imobiliárias (scraping)",
            "document_analysis": "Análise e extração de dados de documentos",
            "weekly_report": "Geração do relatório semanal de erros",
            "error_analysis": "Análise de erros de importação"
        }
        task_defaults = AI_CONFIG_DEFAULTS
    
    # Obter configuração de cache
    cache_config = await db.system_config.find_one({"type": "cache_settings"}, {"_id": 0})
    cache_settings = cache_config or {"cache_limit": 1000, "notify_at_percentage": 80}
    
    return {
        "current_config": current_config,
        "defaults": task_defaults,
        "available_models": available_models,
        "available_providers": available_providers,
        "task_descriptions": task_descriptions,
        "cache_settings": cache_settings
    }


# ============== AI MODELS CRUD ==============

@router.get("/ai-models")
async def list_ai_models(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Lista todos os modelos de IA configurados."""
    from config import AI_MODELS, GEMINI_API_KEY, EMERGENT_LLM_KEY
    
    # Tentar obter da DB
    db_models = await db.ai_models.find({}, {"_id": 0}).to_list(100)
    
    if not db_models:
        # Migrar modelos do config para DB
        for key, model in AI_MODELS.items():
            model_doc = {
                "key": key,
                "name": model["name"],
                "provider": model["provider"],
                "cost_per_1k_tokens": model["cost_per_1k_tokens"],
                "best_for": model["best_for"],
                "requires_key": model.get("requires_key", ""),
                "is_default": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.ai_models.insert_one(model_doc)
        
        db_models = await db.ai_models.find({}, {"_id": 0}).to_list(100)
    
    # Verificar quais providers estão disponíveis
    available_providers = []
    if GEMINI_API_KEY:
        available_providers.append("gemini")
    if EMERGENT_LLM_KEY:
        available_providers.append("openai")
    
    return {
        "models": db_models,
        "available_providers": available_providers
    }


@router.post("/ai-models")
async def create_ai_model(
    model_data: dict,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Adiciona um novo modelo de IA.
    
    Body:
    {
        "key": "claude-3-sonnet",
        "name": "Claude 3 Sonnet",
        "provider": "anthropic",
        "cost_per_1k_tokens": 0.003,
        "best_for": ["analysis", "coding"]
    }
    """
    required_fields = ["key", "name", "provider"]
    for field in required_fields:
        if field not in model_data:
            raise HTTPException(status_code=400, detail=f"Campo '{field}' é obrigatório")
    
    # Verificar se já existe
    existing = await db.ai_models.find_one({"key": model_data["key"]})
    if existing:
        raise HTTPException(status_code=400, detail=f"Modelo '{model_data['key']}' já existe")
    
    model_doc = {
        "key": model_data["key"],
        "name": model_data["name"],
        "provider": model_data["provider"],
        "cost_per_1k_tokens": model_data.get("cost_per_1k_tokens", 0.001),
        "best_for": model_data.get("best_for", []),
        "requires_key": model_data.get("requires_key", ""),
        "is_default": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email", "admin")
    }
    
    await db.ai_models.insert_one(model_doc)
    
    return {"success": True, "model": {k: v for k, v in model_doc.items() if k != "_id"}}


@router.put("/ai-models/{model_key}")
async def update_ai_model(
    model_key: str,
    model_data: dict,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Actualiza um modelo de IA existente."""
    existing = await db.ai_models.find_one({"key": model_key})
    if not existing:
        raise HTTPException(status_code=404, detail=f"Modelo '{model_key}' não encontrado")
    
    update_fields = {}
    allowed_fields = ["name", "provider", "cost_per_1k_tokens", "best_for", "requires_key"]
    
    for field in allowed_fields:
        if field in model_data:
            update_fields[field] = model_data[field]
    
    if update_fields:
        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_fields["updated_by"] = user.get("email", "admin")
        await db.ai_models.update_one({"key": model_key}, {"$set": update_fields})
    
    updated = await db.ai_models.find_one({"key": model_key}, {"_id": 0})
    return {"success": True, "model": updated}


@router.delete("/ai-models/{model_key}")
async def delete_ai_model(
    model_key: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Remove um modelo de IA."""
    existing = await db.ai_models.find_one({"key": model_key})
    if not existing:
        raise HTTPException(status_code=404, detail=f"Modelo '{model_key}' não encontrado")
    
    if existing.get("is_default"):
        raise HTTPException(status_code=400, detail="Não é possível eliminar modelos padrão do sistema")
    
    # Verificar se o modelo está em uso
    ai_config = await db.ai_config.find_one({}, {"_id": 0})
    if ai_config:
        for task, model in ai_config.items():
            if model == model_key:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Modelo está em uso pela tarefa '{task}'. Altere a configuração primeiro."
                )
    
    await db.ai_models.delete_one({"key": model_key})
    return {"success": True, "message": f"Modelo '{model_key}' eliminado"}


# ============== AI TASKS CRUD ==============

@router.get("/ai-tasks")
async def list_ai_tasks(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Lista todas as tarefas de IA configuradas."""
    from config import AI_CONFIG_DEFAULTS
    
    db_tasks = await db.ai_tasks.find({}, {"_id": 0}).to_list(100)
    
    if not db_tasks:
        # Migrar tarefas padrão para DB
        default_tasks = [
            {"key": "scraper_extraction", "description": "Extração de dados de páginas imobiliárias (scraping)", "default_model": "gemini-2.0-flash"},
            {"key": "document_analysis", "description": "Análise e extração de dados de documentos", "default_model": "gpt-4o-mini"},
            {"key": "weekly_report", "description": "Geração do relatório semanal de erros", "default_model": "gpt-4o-mini"},
            {"key": "error_analysis", "description": "Análise de erros de importação", "default_model": "gpt-4o-mini"},
        ]
        
        for task in default_tasks:
            task["is_default"] = True
            task["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.ai_tasks.insert_one(task)
        
        db_tasks = await db.ai_tasks.find({}, {"_id": 0}).to_list(100)
    
    return {"tasks": db_tasks}


@router.post("/ai-tasks")
async def create_ai_task(
    task_data: dict,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Adiciona uma nova tarefa de IA.
    
    Body:
    {
        "key": "lead_scoring",
        "description": "Pontuação automática de leads",
        "default_model": "gpt-4o-mini"
    }
    """
    required_fields = ["key", "description"]
    for field in required_fields:
        if field not in task_data:
            raise HTTPException(status_code=400, detail=f"Campo '{field}' é obrigatório")
    
    existing = await db.ai_tasks.find_one({"key": task_data["key"]})
    if existing:
        raise HTTPException(status_code=400, detail=f"Tarefa '{task_data['key']}' já existe")
    
    task_doc = {
        "key": task_data["key"],
        "description": task_data["description"],
        "default_model": task_data.get("default_model", "gpt-4o-mini"),
        "is_default": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email", "admin")
    }
    
    await db.ai_tasks.insert_one(task_doc)
    return {"success": True, "task": {k: v for k, v in task_doc.items() if k != "_id"}}


@router.put("/ai-tasks/{task_key}")
async def update_ai_task(
    task_key: str,
    task_data: dict,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Actualiza uma tarefa de IA existente."""
    existing = await db.ai_tasks.find_one({"key": task_key})
    if not existing:
        raise HTTPException(status_code=404, detail=f"Tarefa '{task_key}' não encontrada")
    
    update_fields = {}
    if "description" in task_data:
        update_fields["description"] = task_data["description"]
    if "default_model" in task_data:
        update_fields["default_model"] = task_data["default_model"]
    
    if update_fields:
        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.ai_tasks.update_one({"key": task_key}, {"$set": update_fields})
    
    updated = await db.ai_tasks.find_one({"key": task_key}, {"_id": 0})
    return {"success": True, "task": updated}


@router.delete("/ai-tasks/{task_key}")
async def delete_ai_task(
    task_key: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Remove uma tarefa de IA."""
    existing = await db.ai_tasks.find_one({"key": task_key})
    if not existing:
        raise HTTPException(status_code=404, detail=f"Tarefa '{task_key}' não encontrada")
    
    if existing.get("is_default"):
        raise HTTPException(status_code=400, detail="Não é possível eliminar tarefas padrão do sistema")
    
    await db.ai_tasks.delete_one({"key": task_key})
    return {"success": True, "message": f"Tarefa '{task_key}' eliminada"}


# ============== CACHE SETTINGS ==============

@router.get("/cache-settings")
async def get_cache_settings(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Obtém as configurações de cache."""
    config = await db.system_config.find_one({"type": "cache_settings"}, {"_id": 0})
    return config or {
        "type": "cache_settings",
        "cache_limit": 1000,
        "notify_at_percentage": 80,
        "auto_cleanup_enabled": False
    }


@router.put("/cache-settings")
async def update_cache_settings(
    settings: dict,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Actualiza as configurações de cache.
    
    Body:
    {
        "cache_limit": 1000,
        "notify_at_percentage": 80,
        "auto_cleanup_enabled": false
    }
    """
    settings["type"] = "cache_settings"
    settings["updated_at"] = datetime.now(timezone.utc).isoformat()
    settings["updated_by"] = user.get("email", "admin")
    
    await db.system_config.update_one(
        {"type": "cache_settings"},
        {"$set": settings},
        upsert=True
    )
    
    return {"success": True, "settings": settings}


# ============== AI USAGE TRACKING ==============

@router.get("/ai-usage/summary")
async def get_ai_usage_summary(
    period: str = "month",
    task: str = None,
    model: str = None,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """
    Obtém resumo de uso de IA.
    
    Args:
        period: "today", "week", "month", "all"
        task: Filtrar por tarefa específica
        model: Filtrar por modelo específico
    """
    from services.ai_usage_tracker import ai_usage_tracker
    return await ai_usage_tracker.get_usage_summary(period, task, model)


@router.get("/ai-usage/by-task")
async def get_ai_usage_by_task(
    period: str = "month",
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Obtém uso agregado por tarefa."""
    from services.ai_usage_tracker import ai_usage_tracker
    return await ai_usage_tracker.get_usage_by_task(period)


@router.get("/ai-usage/by-model")
async def get_ai_usage_by_model(
    period: str = "month",
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Obtém uso agregado por modelo."""
    from services.ai_usage_tracker import ai_usage_tracker
    return await ai_usage_tracker.get_usage_by_model(period)


@router.get("/ai-usage/trend")
async def get_ai_usage_trend(
    days: int = 30,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Obtém tendência diária de uso dos últimos N dias."""
    from services.ai_usage_tracker import ai_usage_tracker
    return await ai_usage_tracker.get_daily_trend(days)


@router.get("/ai-usage/logs")
async def get_ai_usage_logs(
    limit: int = 50,
    task: str = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Obtém logs recentes de chamadas à IA."""
    from services.ai_usage_tracker import ai_usage_tracker
    return await ai_usage_tracker.get_recent_logs(limit, task)


@router.get("/ai-weekly-report")
async def get_ai_weekly_report(
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """
    Gera relatório semanal de extracções de IA.
    
    Inclui:
    - Total de documentos analisados
    - Taxa de sucesso
    - Campos mais frequentemente extraídos
    - Comparação com semana anterior
    - Distribuição por tipo de documento
    """
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)
    
    # Buscar processos com extracções na última semana
    processes_this_week = await db.processes.find(
        {
            "ai_extraction_history": {"$exists": True, "$ne": []},
        },
        {"_id": 0, "ai_extraction_history": 1, "client_name": 1, "id": 1}
    ).to_list(None)
    
    # Filtrar extracções por período
    this_week_extractions = []
    prev_week_extractions = []
    
    for proc in processes_this_week:
        for extraction in proc.get("ai_extraction_history", []):
            extracted_at = extraction.get("extracted_at", "")
            if extracted_at:
                try:
                    ext_date = datetime.fromisoformat(extracted_at.replace("Z", "+00:00"))
                    if ext_date >= week_start:
                        this_week_extractions.append(extraction)
                    elif ext_date >= prev_week_start:
                        prev_week_extractions.append(extraction)
                except Exception:
                    pass
    
    # Calcular métricas desta semana
    total_this_week = len(this_week_extractions)
    successful_this_week = sum(1 for e in this_week_extractions if e.get("extracted_data"))
    
    # Calcular métricas da semana anterior
    total_prev_week = len(prev_week_extractions)
    successful_prev_week = sum(1 for e in prev_week_extractions if e.get("extracted_data"))
    
    # Taxa de sucesso
    success_rate_this_week = (successful_this_week / total_this_week * 100) if total_this_week > 0 else 0
    success_rate_prev_week = (successful_prev_week / total_prev_week * 100) if total_prev_week > 0 else 0
    
    # Contagem por tipo de documento
    doc_type_counts = {}
    for extraction in this_week_extractions:
        doc_type = extraction.get("document_type", "outro")
        doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
    
    # Campos mais extraídos
    field_counts = {}
    for extraction in this_week_extractions:
        extracted_data = extraction.get("extracted_data", {})
        if isinstance(extracted_data, dict):
            for field, value in extracted_data.items():
                if value:  # Apenas campos com valor
                    field_counts[field] = field_counts.get(field, 0) + 1
    
    # Ordenar campos por frequência
    top_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Mapear nomes de campos para português
    field_labels = {
        "personal_data.nome": "Nome Completo",
        "personal_data.nif": "NIF",
        "personal_data.cc_number": "Nº Cartão Cidadão",
        "personal_data.data_nascimento": "Data de Nascimento",
        "personal_data.morada": "Morada",
        "financial_data.rendimento_mensal": "Rendimento Mensal",
        "financial_data.entidade_patronal": "Entidade Patronal",
        "real_estate_data.valor_imovel": "Valor do Imóvel",
        "client_name": "Nome do Cliente",
        "client_email": "Email",
        "client_phone": "Telefone",
    }
    
    # Mapear tipos de documento
    doc_type_labels = {
        "cc": "Cartão de Cidadão",
        "recibo_vencimento": "Recibo de Vencimento",
        "irs": "Declaração IRS",
        "contrato_trabalho": "Contrato de Trabalho",
        "cpcv": "CPCV",
        "caderneta_predial": "Caderneta Predial",
        "simulacao": "Simulação de Crédito",
        "extrato_bancario": "Extrato Bancário",
        "outro": "Outro Documento",
    }
    
    # Calcular variações
    doc_variation = ((total_this_week - total_prev_week) / total_prev_week * 100) if total_prev_week > 0 else 0
    success_variation = success_rate_this_week - success_rate_prev_week
    
    return {
        "report_date": now.isoformat(),
        "period": {
            "start": week_start.isoformat(),
            "end": now.isoformat()
        },
        "summary": {
            "total_documents_analyzed": total_this_week,
            "successful_extractions": successful_this_week,
            "success_rate": round(success_rate_this_week, 1),
            "comparison": {
                "prev_week_total": total_prev_week,
                "prev_week_success_rate": round(success_rate_prev_week, 1),
                "documents_variation_percent": round(doc_variation, 1),
                "success_rate_variation": round(success_variation, 1)
            }
        },
        "by_document_type": [
            {
                "type": doc_type,
                "label": doc_type_labels.get(doc_type, doc_type),
                "count": count,
                "percentage": round(count / total_this_week * 100, 1) if total_this_week > 0 else 0
            }
            for doc_type, count in sorted(doc_type_counts.items(), key=lambda x: x[1], reverse=True)
        ],
        "top_extracted_fields": [
            {
                "field": field,
                "label": field_labels.get(field, field),
                "count": count,
                "percentage": round(count / total_this_week * 100, 1) if total_this_week > 0 else 0
            }
            for field, count in top_fields
        ],
        "insights": _generate_ai_insights(total_this_week, success_rate_this_week, doc_variation, success_variation)
    }


def _generate_ai_insights(total: int, success_rate: float, doc_variation: float, success_variation: float) -> list:
    """Gera insights automáticos baseados nos dados."""
    insights = []
    
    if total == 0:
        insights.append({
            "type": "info",
            "message": "Nenhum documento analisado esta semana. Considere testar a funcionalidade de análise de documentos."
        })
        return insights
    
    # Insight sobre volume
    if doc_variation > 20:
        insights.append({
            "type": "success",
            "message": f"Excelente! O volume de documentos analisados aumentou {doc_variation:.0f}% em relação à semana anterior."
        })
    elif doc_variation < -20:
        insights.append({
            "type": "warning",
            "message": f"O volume de documentos analisados diminuiu {abs(doc_variation):.0f}% em relação à semana anterior."
        })
    
    # Insight sobre taxa de sucesso
    if success_rate >= 90:
        insights.append({
            "type": "success",
            "message": f"Taxa de sucesso excelente: {success_rate:.1f}% dos documentos foram extraídos com sucesso."
        })
    elif success_rate >= 70:
        insights.append({
            "type": "info",
            "message": f"Taxa de sucesso boa: {success_rate:.1f}%. Há espaço para melhorias na qualidade dos documentos enviados."
        })
    else:
        insights.append({
            "type": "warning",
            "message": f"Taxa de sucesso baixa: {success_rate:.1f}%. Verifique a qualidade das imagens e PDFs enviados."
        })
    
    # Insight sobre variação da taxa
    if success_variation > 5:
        insights.append({
            "type": "success",
            "message": f"A taxa de sucesso melhorou {success_variation:.1f} pontos percentuais em relação à semana anterior!"
        })
    elif success_variation < -5:
        insights.append({
            "type": "warning",
            "message": f"A taxa de sucesso diminuiu {abs(success_variation):.1f} pontos percentuais. Investigue possíveis causas."
        })
    
    return insights


@router.put("/ai-config")
async def update_ai_configuration(
    config: dict,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Actualiza a configuração de IA.
    
    Body:
    {
        "scraper_extraction": "gemini-1.5-flash",
        "document_analysis": "gpt-4o-mini",
        "weekly_report": "gpt-4o-mini",
        "error_analysis": "gpt-4o-mini"
    }
    """
    from config import AI_MODELS
    from services.ai_page_analyzer import save_ai_config
    
    # Validar modelos
    for task, model in config.items():
        if model not in AI_MODELS:
            raise HTTPException(
                status_code=400, 
                detail=f"Modelo '{model}' não existe. Disponíveis: {list(AI_MODELS.keys())}"
            )
    
    await save_ai_config(config, user.get("email", "admin"))
    
    return {
        "success": True,
        "message": "Configuração de IA actualizada",
        "new_config": config
    }


@router.post("/ai-test")
async def test_ai_configuration(
    model: str = "gemini-1.5-flash",
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Testa se um modelo de IA está a funcionar correctamente.
    """
    from config import AI_MODELS, GEMINI_API_KEY, EMERGENT_LLM_KEY
    
    if model not in AI_MODELS:
        raise HTTPException(status_code=400, detail=f"Modelo '{model}' não existe")
    
    model_info = AI_MODELS[model]
    provider = model_info["provider"]
    
    # Verificar se a chave está configurada
    if provider == "gemini" and not GEMINI_API_KEY:
        return {"success": False, "error": "GEMINI_API_KEY não configurada"}
    if provider == "openai" and not EMERGENT_LLM_KEY:
        return {"success": False, "error": "EMERGENT_LLM_KEY não configurada"}
    
    try:
        if provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model_instance = genai.GenerativeModel("gemini-2.0-flash")
            response = model_instance.generate_content("Responde apenas: OK")
            result = response.text.strip()
            return {"success": True, "model": model, "response": result}
        
        elif provider == "openai":
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id="test",
                system_message="Responde apenas: OK"
            ).with_model("openai", model)
            response = await chat.send_message(UserMessage(text="Teste"))
            return {"success": True, "model": model, "response": response.strip()}
        
    except Exception as e:
        return {"success": False, "model": model, "error": str(e)}


# ============== NOTIFICATION PREFERENCES ==============

# Default notification preferences
DEFAULT_NOTIFICATION_PREFS = {
    "email_new_process": False,  # Novo processo criado
    "email_status_change": False,  # Mudança de status de processo
    "email_document_upload": False,  # Documento carregado
    "email_task_assigned": False,  # Tarefa atribuída
    "email_deadline_reminder": True,  # Lembrete de prazo (importante)
    "email_urgent_only": True,  # Apenas urgentes
    "email_daily_summary": True,  # Resumo diário
    "email_weekly_report": True,  # Relatório semanal
    "inapp_new_process": True,
    "inapp_status_change": True,
    "inapp_document_upload": True,
    "inapp_task_assigned": True,
    "inapp_comments": True,
    "is_test_user": False,  # Se true, não recebe emails
}


@router.get("/notification-preferences/{user_id}")
async def get_notification_preferences(
    user_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Obtém as preferências de notificação de um utilizador.
    Admin pode ver/editar de qualquer utilizador.
    """
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    
    # Obter preferências da DB ou usar defaults
    prefs = await db.notification_preferences.find_one({"user_id": user_id}, {"_id": 0})
    
    if not prefs:
        prefs = {**DEFAULT_NOTIFICATION_PREFS, "user_id": user_id}
    
    return {
        "user_id": user_id,
        "user_email": target_user.get("email"),
        "user_name": target_user.get("name"),
        "preferences": prefs
    }


@router.put("/notification-preferences/{user_id}")
async def update_notification_preferences(
    user_id: str,
    preferences: dict,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Actualiza as preferências de notificação de um utilizador.
    Admin pode editar de qualquer utilizador.
    """
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    
    # Filtrar apenas campos válidos
    valid_keys = set(DEFAULT_NOTIFICATION_PREFS.keys())
    filtered_prefs = {k: v for k, v in preferences.items() if k in valid_keys}
    
    filtered_prefs["user_id"] = user_id
    filtered_prefs["updated_at"] = datetime.now(timezone.utc).isoformat()
    filtered_prefs["updated_by"] = user.get("email", "admin")
    
    await db.notification_preferences.update_one(
        {"user_id": user_id},
        {"$set": filtered_prefs},
        upsert=True
    )
    
    return {"success": True, "preferences": filtered_prefs}


@router.get("/notification-preferences")
async def get_all_notification_preferences(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Lista preferências de todos os utilizadores."""
    users = await db.users.find({}, {"_id": 0, "id": 1, "email": 1, "name": 1, "role": 1}).to_list(500)
    
    result = []
    for u in users:
        prefs = await db.notification_preferences.find_one({"user_id": u["id"]}, {"_id": 0})
        if not prefs:
            prefs = {**DEFAULT_NOTIFICATION_PREFS, "user_id": u["id"]}
        
        result.append({
            "user_id": u["id"],
            "email": u.get("email"),
            "name": u.get("name"),
            "role": u.get("role"),
            "receives_email": not prefs.get("is_test_user", False) and (
                prefs.get("email_urgent_only") or 
                prefs.get("email_daily_summary") or
                prefs.get("email_weekly_report")
            ),
            "is_test_user": prefs.get("is_test_user", False)
        })
    
    return result


@router.post("/notification-preferences/bulk-update")
async def bulk_update_notification_preferences(
    data: dict,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Actualiza preferências de múltiplos utilizadores de uma vez.
    
    Body:
    {
        "user_ids": ["id1", "id2"],
        "preferences": {"is_test_user": true}
    }
    """
    user_ids = data.get("user_ids", [])
    preferences = data.get("preferences", {})
    
    if not user_ids:
        raise HTTPException(status_code=400, detail="user_ids é obrigatório")
    
    valid_keys = set(DEFAULT_NOTIFICATION_PREFS.keys())
    filtered_prefs = {k: v for k, v in preferences.items() if k in valid_keys}
    filtered_prefs["updated_at"] = datetime.now(timezone.utc).isoformat()
    filtered_prefs["updated_by"] = user.get("email", "admin")
    
    updated = 0
    for uid in user_ids:
        result = await db.notification_preferences.update_one(
            {"user_id": uid},
            {"$set": {**filtered_prefs, "user_id": uid}},
            upsert=True
        )
        if result.modified_count > 0 or result.upserted_id:
            updated += 1
    
    return {"success": True, "updated_count": updated}


# ============== SYSTEM ERROR LOGS ==============

@router.get("/system-logs")
async def get_system_error_logs(
    page: int = 1,
    limit: int = 50,
    severity: str = None,
    component: str = None,
    error_type: str = None,
    resolved: bool = None,
    days: int = 7,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Obtém logs de erros do sistema com filtros e paginação.
    
    Query params:
    - page: Página (default 1)
    - limit: Items por página (default 50)
    - severity: Filtrar por severidade (info, warning, error, critical)
    - component: Filtrar por componente (scraper, auth, processes, etc.)
    - error_type: Filtrar por tipo de erro
    - resolved: True/False para filtrar resolvidos/não resolvidos
    - days: Últimos N dias (default 7)
    """
    from services.system_error_logger import system_error_logger
    return await system_error_logger.get_errors(
        page=page,
        limit=limit,
        severity=severity,
        component=component,
        error_type=error_type,
        resolved=resolved,
        days=days
    )


@router.get("/system-logs/stats")
async def get_system_logs_stats(
    days: int = 7,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Obtém estatísticas de erros dos últimos N dias."""
    from services.system_error_logger import system_error_logger
    return await system_error_logger.get_stats(days)


@router.get("/system-logs/{error_id}")
async def get_system_log_detail(
    error_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Obtém detalhes de um erro específico."""
    from services.system_error_logger import system_error_logger
    error = await system_error_logger.get_error_by_id(error_id)
    if not error:
        raise HTTPException(status_code=404, detail="Erro não encontrado")
    return error


@router.post("/system-logs/mark-read")
async def mark_errors_as_read(
    data: dict,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Marca erros como lidos.
    
    Body: {"error_ids": ["id1", "id2"]}
    """
    error_ids = data.get("error_ids", [])
    if not error_ids:
        raise HTTPException(status_code=400, detail="error_ids é obrigatório")
    
    from services.system_error_logger import system_error_logger
    count = await system_error_logger.mark_as_read(error_ids)
    return {"success": True, "marked_count": count}


@router.post("/system-logs/{error_id}/resolve")
async def resolve_system_error(
    error_id: str,
    data: dict = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Marca um erro como resolvido.
    
    Body (opcional): {"notes": "Corrigido em versão X"}
    """
    data = data or {}
    notes = data.get("notes")
    
    from services.system_error_logger import system_error_logger
    success = await system_error_logger.mark_as_resolved(
        error_id=error_id,
        resolved_by=user.get("email", "admin"),
        notes=notes
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Erro não encontrado")
    
    return {"success": True, "message": "Erro marcado como resolvido"}


@router.delete("/system-logs/cleanup")
async def cleanup_old_system_logs(
    days: int = 90,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Remove logs antigos (mais de N dias)."""
    from services.system_error_logger import system_error_logger
    count = await system_error_logger.cleanup_old_errors(days)
    return {"success": True, "deleted_count": count}

