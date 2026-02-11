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
