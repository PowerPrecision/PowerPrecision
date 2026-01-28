"""
====================================================================
ROTAS DE TAREFAS - CREDITOIMO
====================================================================
Endpoints para gestão de tarefas.
====================================================================
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from database import db
from models.task import TaskCreate, TaskUpdate, TaskResponse
from services.auth import get_current_user
from services.realtime_notifications import send_realtime_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def get_user_names(user_ids: List[str]) -> dict:
    """Obter nomes dos utilizadores por ID."""
    users = await db.users.find(
        {"id": {"$in": user_ids}},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(100)
    return {u["id"]: u["name"] for u in users}


async def enrich_task(task: dict) -> dict:
    """Adicionar nomes de utilizadores e processo à tarefa."""
    # Obter nomes dos utilizadores atribuídos
    if task.get("assigned_to"):
        user_names = await get_user_names(task["assigned_to"])
        task["assigned_to_names"] = [user_names.get(uid, "Desconhecido") for uid in task["assigned_to"]]
    
    # Obter nome do criador
    if task.get("created_by"):
        creator_names = await get_user_names([task["created_by"]])
        task["created_by_name"] = creator_names.get(task["created_by"], "Desconhecido")
    
    # Obter nome do processo/cliente
    if task.get("process_id"):
        process = await db.processes.find_one(
            {"id": task["process_id"]},
            {"_id": 0, "client_name": 1}
        )
        if process:
            task["process_name"] = process.get("client_name", "")
    
    return task


@router.post("", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Criar nova tarefa.
    Qualquer utilizador pode criar tarefas e atribuir a qualquer pessoa.
    """
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Construir título com nome do processo se aplicável
    title = task_data.title
    process_name = None
    
    if task_data.process_id:
        process = await db.processes.find_one(
            {"id": task_data.process_id},
            {"_id": 0, "client_name": 1}
        )
        if process:
            process_name = process.get("client_name", "")
            # Se o título não contém o nome do cliente, adicionar
            if process_name and process_name not in title:
                title = f"[{process_name}] {title}"
    
    task = {
        "id": task_id,
        "title": title,
        "description": task_data.description,
        "assigned_to": task_data.assigned_to,
        "process_id": task_data.process_id,
        "created_by": current_user["id"],
        "completed": False,
        "completed_at": None,
        "completed_by": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.tasks.insert_one(task)
    logger.info(f"Tarefa criada: {task_id} por {current_user['name']}")
    
    # Enviar notificações para os utilizadores atribuídos
    for user_id in task_data.assigned_to:
        if user_id != current_user["id"]:  # Não notificar o criador
            await send_realtime_notification(
                user_id=user_id,
                title="📋 Nova Tarefa Atribuída",
                message=f"{current_user['name']} atribuiu-lhe uma tarefa: {title}",
                notification_type="task_assigned",
                link=f"/tasks" if not task_data.process_id else f"/process/{task_data.process_id}",
                process_id=task_data.process_id
            )
    
    # Retornar tarefa enriquecida
    enriched = await enrich_task(task)
    return TaskResponse(**enriched)


@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    process_id: Optional[str] = Query(None, description="Filtrar por processo"),
    assigned_to_me: bool = Query(False, description="Apenas tarefas atribuídas a mim"),
    created_by_me: bool = Query(False, description="Apenas tarefas criadas por mim"),
    include_completed: bool = Query(False, description="Incluir tarefas concluídas"),
    current_user: dict = Depends(get_current_user)
):
    """
    Listar tarefas.
    
    Filtros:
    - process_id: Filtrar por processo específico
    - assigned_to_me: Apenas tarefas atribuídas ao utilizador atual
    - created_by_me: Apenas tarefas criadas pelo utilizador atual
    - include_completed: Incluir tarefas já concluídas
    """
    query = {}
    
    # Filtro por processo
    if process_id:
        query["process_id"] = process_id
    
    # Filtro por atribuição
    if assigned_to_me:
        query["assigned_to"] = current_user["id"]
    
    # Filtro por criador
    if created_by_me:
        query["created_by"] = current_user["id"]
    
    # Filtro por estado
    if not include_completed:
        query["completed"] = False
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Enriquecer tarefas com nomes
    enriched_tasks = []
    for task in tasks:
        enriched = await enrich_task(task)
        enriched_tasks.append(TaskResponse(**enriched))
    
    return enriched_tasks


@router.get("/my-tasks", response_model=List[TaskResponse])
async def get_my_tasks(
    include_completed: bool = Query(False),
    current_user: dict = Depends(get_current_user)
):
    """
    Listar tarefas atribuídas ao utilizador atual.
    """
    query = {
        "assigned_to": current_user["id"]
    }
    
    if not include_completed:
        query["completed"] = False
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    enriched_tasks = []
    for task in tasks:
        enriched = await enrich_task(task)
        enriched_tasks.append(TaskResponse(**enriched))
    
    return enriched_tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obter detalhes de uma tarefa."""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    enriched = await enrich_task(task)
    return TaskResponse(**enriched)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Atualizar uma tarefa."""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if task_data.title is not None:
        update_data["title"] = task_data.title
    if task_data.description is not None:
        update_data["description"] = task_data.description
    if task_data.assigned_to is not None:
        update_data["assigned_to"] = task_data.assigned_to
        # Notificar novos utilizadores
        new_assignees = set(task_data.assigned_to) - set(task.get("assigned_to", []))
        for user_id in new_assignees:
            if user_id != current_user["id"]:
                await send_realtime_notification(
                    user_id=user_id,
                    title="📋 Nova Tarefa Atribuída",
                    message=f"{current_user['name']} atribuiu-lhe uma tarefa: {task['title']}",
                    notification_type="task_assigned",
                    link=f"/tasks" if not task.get("process_id") else f"/process/{task['process_id']}",
                    process_id=task.get("process_id")
                )
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    enriched = await enrich_task(updated_task)
    return TaskResponse(**enriched)


@router.put("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Marcar tarefa como concluída."""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "completed": True,
            "completed_at": now,
            "completed_by": current_user["id"],
            "updated_at": now
        }}
    )
    
    logger.info(f"Tarefa {task_id} marcada como concluída por {current_user['name']}")
    
    # Notificar o criador se for diferente de quem concluiu
    if task["created_by"] != current_user["id"]:
        await send_realtime_notification(
            user_id=task["created_by"],
            title="✅ Tarefa Concluída",
            message=f"{current_user['name']} concluiu a tarefa: {task['title']}",
            notification_type="task_completed",
            link=f"/tasks" if not task.get("process_id") else f"/process/{task['process_id']}",
            process_id=task.get("process_id")
        )
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    enriched = await enrich_task(updated_task)
    return TaskResponse(**enriched)


@router.put("/{task_id}/reopen", response_model=TaskResponse)
async def reopen_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Reabrir tarefa concluída."""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "completed": False,
            "completed_at": None,
            "completed_by": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    enriched = await enrich_task(updated_task)
    return TaskResponse(**enriched)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar tarefa."""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    # Apenas o criador ou admin pode eliminar
    if task["created_by"] != current_user["id"] and current_user["role"] not in ["admin", "ceo"]:
        raise HTTPException(status_code=403, detail="Sem permissão para eliminar esta tarefa")
    
    await db.tasks.delete_one({"id": task_id})
    logger.info(f"Tarefa {task_id} eliminada por {current_user['name']}")
    
    return {"success": True, "message": "Tarefa eliminada"}
