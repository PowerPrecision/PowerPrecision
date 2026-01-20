from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from database import db
from models.auth import UserRole
from services.auth import get_current_user


router = APIRouter(tags=["Stats"])


@router.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    stats = {}
    
    statuses = await db.workflow_statuses.find({}, {"_id": 0}).to_list(100)
    
    if user["role"] == UserRole.CLIENTE:
        stats["total_processes"] = await db.processes.count_documents({"client_id": user["id"]})
        stats["pending_deadlines"] = await db.deadlines.count_documents({
            "process_id": {"$in": [p["id"] for p in await db.processes.find({"client_id": user["id"]}, {"id": 1}).to_list(100)]},
            "completed": False
        })
    elif user["role"] in [UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.ADMIN]:
        stats["total_processes"] = await db.processes.count_documents({})
        
        for status in statuses:
            stats[f"status_{status['name']}"] = await db.processes.count_documents({"status": status["name"]})
        
        if not statuses:
            stats["pending_processes"] = await db.processes.count_documents({"status": "pedido_inicial"})
            stats["in_analysis"] = await db.processes.count_documents({"status": "em_analise"})
            stats["bank_authorization"] = await db.processes.count_documents({"status": "autorizacao_bancaria"})
            stats["approved"] = await db.processes.count_documents({"status": "aprovado"})
            stats["rejected"] = await db.processes.count_documents({"status": "rejeitado"})
        
        stats["total_deadlines"] = await db.deadlines.count_documents({})
        stats["pending_deadlines"] = await db.deadlines.count_documents({"completed": False})
    
    if user["role"] == UserRole.ADMIN:
        stats["total_users"] = await db.users.count_documents({})
        stats["clients"] = await db.users.count_documents({"role": UserRole.CLIENTE})
        stats["consultors"] = await db.users.count_documents({"role": UserRole.CONSULTOR})
        stats["mediadors"] = await db.users.count_documents({"role": UserRole.MEDIADOR})
    
    return stats


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
