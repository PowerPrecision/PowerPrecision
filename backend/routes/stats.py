from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from database import db
from models.auth import UserRole
from services.auth import get_current_user


router = APIRouter(tags=["Stats"])


@router.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    """Get statistics based on user role. Staff see only their assigned processes."""
    stats = {}
    role = user["role"]
    user_id = user["id"]
    
    # Build query based on role
    process_query = {}
    
    if role == UserRole.CLIENTE:
        process_query = {"client_id": user_id}
    elif role == UserRole.CONSULTOR:
        process_query = {"assigned_consultor_id": user_id}
    elif role in [UserRole.MEDIADOR, UserRole.INTERMEDIARIO]:
        process_query = {"assigned_mediador_id": user_id}
    elif role == UserRole.DIRETOR:
        process_query = {"$or": [
            {"assigned_consultor_id": user_id},
            {"assigned_mediador_id": user_id}
        ]}
    # Admin, CEO e Administrativo see all (no filter)
    
    # Get process count
    stats["total_processes"] = await db.processes.count_documents(process_query)
    
    # Process status breakdown
    # Active = not concluded and not dropped out
    concluded_statuses = ["concluidos"]
    dropped_statuses = ["desistencias"]
    
    concluded_query = {**process_query, "status": {"$in": concluded_statuses}} if process_query else {"status": {"$in": concluded_statuses}}
    dropped_query = {**process_query, "status": {"$in": dropped_statuses}} if process_query else {"status": {"$in": dropped_statuses}}
    active_query = {**process_query, "status": {"$nin": concluded_statuses + dropped_statuses}} if process_query else {"status": {"$nin": concluded_statuses + dropped_statuses}}
    
    stats["active_processes"] = await db.processes.count_documents(active_query)
    stats["concluded_processes"] = await db.processes.count_documents(concluded_query)
    stats["dropped_processes"] = await db.processes.count_documents(dropped_query)
    
    # Get process IDs que o utilizador tem acesso (para contar prazos)
    if role in [UserRole.ADMIN, UserRole.CEO, UserRole.ADMINISTRATIVO]:
        # Admin, CEO e Administrativo vêem todos os prazos pendentes
        pending_deadlines_count = await db.deadlines.count_documents({"completed": False})
    elif role == UserRole.CLIENTE:
        # Clientes vêem apenas prazos dos seus processos
        my_processes = await db.processes.find({"client_id": user_id}, {"id": 1, "_id": 0}).to_list(1000)
        my_process_ids = [p["id"] for p in my_processes]
        pending_deadlines_count = await db.deadlines.count_documents({
            "process_id": {"$in": my_process_ids}, 
            "completed": False
        }) if my_process_ids else 0
    else:
        # Consultores/Intermediários/Diretores vêem apenas prazos dos processos que lhes estão atribuídos
        my_processes = await db.processes.find({
            "$or": [
                {"assigned_consultor_id": user_id},
                {"consultor_id": user_id},
                {"assigned_mediador_id": user_id},
                {"intermediario_id": user_id}
            ]
        }, {"id": 1, "_id": 0}).to_list(1000)
        my_process_ids = [p["id"] for p in my_processes]
        
        # Contar prazos dos processos atribuídos OU criados pelo utilizador
        if my_process_ids:
            pending_deadlines_count = await db.deadlines.count_documents({
                "$or": [
                    {"process_id": {"$in": my_process_ids}, "completed": False},
                    {"created_by": user_id, "process_id": None, "completed": False}
                ]
            })
        else:
            pending_deadlines_count = await db.deadlines.count_documents({
                "created_by": user_id, 
                "process_id": None, 
                "completed": False
            })
    
    # Tarefas pendentes atribuídas ao utilizador
    task_query = {"completed": False, "assigned_to": user_id}
    pending_tasks_count = await db.tasks.count_documents(task_query)
    
    # Total de pendentes = prazos + tarefas
    stats["pending_deadlines"] = pending_deadlines_count
    stats["pending_tasks"] = pending_tasks_count
    stats["total_pending"] = pending_deadlines_count + pending_tasks_count
    
    # User stats (Admin and CEO only)
    if role in [UserRole.ADMIN, UserRole.CEO]:
        stats["total_users"] = await db.users.count_documents({})
        stats["active_users"] = await db.users.count_documents({"is_active": {"$ne": False}})
        stats["inactive_users"] = await db.users.count_documents({"is_active": False})
        stats["clients"] = await db.users.count_documents({"role": UserRole.CLIENTE})
        stats["consultors"] = await db.users.count_documents({"role": {"$in": [UserRole.CONSULTOR, UserRole.DIRETOR]}})
        stats["intermediarios"] = await db.users.count_documents({"role": {"$in": [UserRole.MEDIADOR, UserRole.INTERMEDIARIO, UserRole.DIRETOR]}})
    
    return stats


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
