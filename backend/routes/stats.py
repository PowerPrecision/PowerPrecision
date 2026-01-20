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
    elif role == UserRole.MEDIADOR:
        process_query = {"assigned_mediador_id": user_id}
    elif role == UserRole.CONSULTOR_MEDIADOR:
        process_query = {"$or": [
            {"assigned_consultor_id": user_id},
            {"assigned_mediador_id": user_id}
        ]}
    # Admin and CEO see all (no filter)
    
    # Get process count
    stats["total_processes"] = await db.processes.count_documents(process_query)
    
    # Get process IDs for deadline query
    if process_query:
        process_ids = [p["id"] for p in await db.processes.find(process_query, {"id": 1, "_id": 0}).to_list(1000)]
        deadline_query = {"process_id": {"$in": process_ids}} if process_ids else {"process_id": {"$in": []}}
    else:
        deadline_query = {}
    
    # Deadlines
    stats["total_deadlines"] = await db.deadlines.count_documents(deadline_query)
    stats["pending_deadlines"] = await db.deadlines.count_documents({**deadline_query, "completed": False})
    
    # Status breakdown (for staff)
    if UserRole.is_staff(role):
        statuses = await db.workflow_statuses.find({}, {"_id": 0}).to_list(100)
        for status in statuses:
            status_query = {**process_query, "status": status["name"]} if process_query else {"status": status["name"]}
            stats[f"status_{status['name']}"] = await db.processes.count_documents(status_query)
    
    # User stats (Admin and CEO only)
    if role in [UserRole.ADMIN, UserRole.CEO]:
        stats["total_users"] = await db.users.count_documents({})
        stats["clients"] = await db.users.count_documents({"role": UserRole.CLIENTE})
        stats["consultors"] = await db.users.count_documents({"role": {"$in": [UserRole.CONSULTOR, UserRole.CONSULTOR_MEDIADOR]}})
        stats["mediadors"] = await db.users.count_documents({"role": {"$in": [UserRole.MEDIADOR, UserRole.CONSULTOR_MEDIADOR]}})
    
    return stats


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
