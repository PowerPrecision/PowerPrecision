"""
====================================================================
ROTAS DE EMAILS - CREDITOIMO
====================================================================
Endpoints para gestão de histórico de emails.

TAREFA 1 (Iteração 42):
- Filtrar emails por participação do utilizador (privacidade)
- Permitir associação manual de emails a clientes
====================================================================
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from database import db
from models.email import EmailCreate, EmailUpdate, EmailResponse, EmailDirection, EmailStatus
from services.auth import get_current_user
from services.email_service import sync_emails_for_process, send_email, test_email_connection, get_email_accounts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["Emails"])


async def enrich_email(email: dict) -> dict:
    """Adicionar nomes ao email."""
    # Nome do processo/cliente
    if email.get("process_id"):
        process = await db.processes.find_one(
            {"id": email["process_id"]},
            {"_id": 0, "client_name": 1}
        )
        if process:
            email["client_name"] = process.get("client_name", "")
    
    # Nome de quem criou
    if email.get("created_by"):
        user = await db.users.find_one(
            {"id": email["created_by"]},
            {"_id": 0, "name": 1}
        )
        if user:
            email["created_by_name"] = user.get("name", "")
    
    return email


# ==== ROTAS ESPECÍFICAS (devem vir antes das genéricas) ====

@router.get("/test-connection")
async def test_email_connections(
    account: Optional[str] = Query(None, description="Conta específica (precision, power) ou todas"),
    current_user: dict = Depends(get_current_user)
):
    """
    Testar conexão com as contas de email.
    """
    # Apenas admin pode testar
    if current_user["role"] not in ["admin", "ceo"]:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    results = await test_email_connection(account)
    return results


@router.get("/accounts")
async def get_configured_accounts(
    current_user: dict = Depends(get_current_user)
):
    """
    Listar contas de email configuradas.
    """
    accounts = get_email_accounts()
    return [
        {
            "name": a.name,
            "email": a.email,
            "imap_server": a.imap_server,
            "smtp_server": a.smtp_server
        }
        for a in accounts
    ]


@router.get("/process/{process_id}", response_model=List[EmailResponse])
async def get_process_emails(
    process_id: str,
    direction: Optional[EmailDirection] = Query(None, description="Filtrar por direção"),
    current_user: dict = Depends(get_current_user)
):
    """
    Listar emails de um processo.
    """
    query = {"process_id": process_id}
    
    if direction:
        query["direction"] = direction.value
    
    emails = await db.emails.find(query, {"_id": 0}).sort("sent_at", -1).to_list(500)
    
    enriched_emails = []
    for email in emails:
        enriched = await enrich_email(email)
        enriched_emails.append(EmailResponse(**enriched))
    
    return enriched_emails


@router.get("/stats/{process_id}")
async def get_email_stats(
    process_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obter estatísticas de emails de um processo."""
    pipeline = [
        {"$match": {"process_id": process_id}},
        {"$group": {
            "_id": "$direction",
            "count": {"$sum": 1}
        }}
    ]
    
    results = await db.emails.aggregate(pipeline).to_list(10)
    
    stats = {
        "total": 0,
        "sent": 0,
        "received": 0
    }
    
    for r in results:
        if r["_id"] == "sent":
            stats["sent"] = r["count"]
        elif r["_id"] == "received":
            stats["received"] = r["count"]
        stats["total"] += r["count"]
    
    return stats


@router.post("/sync/{process_id}")
async def sync_process_emails(
    process_id: str,
    days: int = Query(30, description="Sincronizar emails dos últimos X dias"),
    current_user: dict = Depends(get_current_user)
):
    """
    Sincronizar emails de um processo.
    Busca emails das contas configuradas (Precision e Power) 
    relacionados com o email do cliente.
    """
    result = await sync_emails_for_process(process_id, days)
    return result


@router.post("/send")
async def send_email_endpoint(
    to_emails: List[str],
    subject: str,
    body: str,
    body_html: Optional[str] = None,
    cc_emails: Optional[List[str]] = None,
    account: str = Query("precision", description="Conta de email (precision ou power)"),
    process_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar email através de uma das contas configuradas.
    """
    result = await send_email(
        account_name=account,
        to_emails=to_emails,
        subject=subject,
        body=body,
        body_html=body_html,
        cc_emails=cc_emails,
        process_id=process_id,
        created_by=current_user["id"]
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Erro ao enviar email"))
    
    return result


# ==== ROTAS CRUD GENÉRICAS ====

@router.post("", response_model=EmailResponse)
async def create_email_record(
    email_data: EmailCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Registar um email no histórico.
    Pode ser usado para:
    - Emails enviados pela aplicação
    - Emails adicionados manualmente
    """
    email_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    email = {
        "id": email_id,
        "process_id": email_data.process_id,
        "direction": email_data.direction.value,
        "from_email": email_data.from_email,
        "to_emails": email_data.to_emails,
        "cc_emails": email_data.cc_emails or [],
        "bcc_emails": email_data.bcc_emails or [],
        "subject": email_data.subject,
        "body": email_data.body,
        "body_html": email_data.body_html,
        "attachments": [a.dict() for a in (email_data.attachments or [])],
        "status": email_data.status.value,
        "sent_at": email_data.sent_at or now,
        "created_at": now,
        "created_by": current_user["id"],
        "notes": email_data.notes
    }
    
    await db.emails.insert_one(email)
    logger.info(f"Email registado: {email_id} para processo {email_data.process_id}")
    
    enriched = await enrich_email(email)
    return EmailResponse(**enriched)


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obter detalhes de um email."""
    email = await db.emails.find_one({"id": email_id}, {"_id": 0})
    
    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado")
    
    enriched = await enrich_email(email)
    return EmailResponse(**enriched)


@router.put("/{email_id}", response_model=EmailResponse)
async def update_email(
    email_id: str,
    email_data: EmailUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Atualizar registo de email (notas, status)."""
    email = await db.emails.find_one({"id": email_id}, {"_id": 0})
    
    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado")
    
    update_data = {}
    if email_data.subject is not None:
        update_data["subject"] = email_data.subject
    if email_data.body is not None:
        update_data["body"] = email_data.body
    if email_data.notes is not None:
        update_data["notes"] = email_data.notes
    if email_data.status is not None:
        update_data["status"] = email_data.status.value
    
    if update_data:
        await db.emails.update_one({"id": email_id}, {"$set": update_data})
    
    updated_email = await db.emails.find_one({"id": email_id}, {"_id": 0})
    enriched = await enrich_email(updated_email)
    return EmailResponse(**enriched)


@router.delete("/{email_id}")
async def delete_email(
    email_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar registo de email."""
    email = await db.emails.find_one({"id": email_id}, {"_id": 0})
    
    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado")
    
    await db.emails.delete_one({"id": email_id})
    logger.info(f"Email {email_id} eliminado por {current_user['name']}")
    
    return {"success": True, "message": "Email eliminado"}



# ==== GESTÃO DE EMAILS MONITORIZADOS ====

@router.get("/monitored/{process_id}")
async def get_monitored_emails(
    process_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obter lista de emails monitorizados de um processo.
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0, "client_email": 1, "monitored_emails": 1})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    return {
        "client_email": process.get("client_email"),
        "monitored_emails": process.get("monitored_emails", [])
    }


@router.post("/monitored/{process_id}")
async def add_monitored_email(
    process_id: str,
    email: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Adicionar email à lista de monitorizados de um processo.
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Validar email
    email = email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Email inválido")
    
    # Obter lista atual
    monitored = process.get("monitored_emails", [])
    
    # Verificar se já existe
    if email in monitored or email == process.get("client_email", "").lower():
        raise HTTPException(status_code=400, detail="Email já está na lista")
    
    # Adicionar
    monitored.append(email)
    await db.processes.update_one(
        {"id": process_id},
        {"$set": {"monitored_emails": monitored}}
    )
    
    logger.info(f"Email {email} adicionado à monitorização do processo {process_id}")
    
    return {
        "success": True,
        "monitored_emails": monitored
    }


@router.delete("/monitored/{process_id}/{email}")
async def remove_monitored_email(
    process_id: str,
    email: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remover email da lista de monitorizados.
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    email = email.lower().strip()
    monitored = process.get("monitored_emails", [])
    
    if email not in monitored:
        raise HTTPException(status_code=404, detail="Email não encontrado na lista")
    
    monitored.remove(email)
    await db.processes.update_one(
        {"id": process_id},
        {"$set": {"monitored_emails": monitored}}
    )
    
    logger.info(f"Email {email} removido da monitorização do processo {process_id}")
    
    return {
        "success": True,
        "monitored_emails": monitored
    }
