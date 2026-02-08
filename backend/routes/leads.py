"""
Rotas para gestão de Leads de Imóveis
"""
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query

from database import db
from models.lead import (
    PropertyLead, PropertyLeadCreate, PropertyLeadUpdate,
    LeadStatus, LeadHistory, ScrapedData
)
from services.property_scraper import extract_property_data
from services.auth import get_current_user, require_roles
from models.user import UserRole

router = APIRouter(prefix="/leads", tags=["Property Leads"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[PropertyLead])
async def list_leads(
    status: Optional[LeadStatus] = None,
    client_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Listar todos os leads de imóveis."""
    query = {}
    
    if status:
        query["status"] = status
    if client_id:
        query["client_id"] = client_id
    
    leads = await db.property_leads.find(query, {"_id": 0}).to_list(length=500)
    
    # Enriquecer com nome do cliente
    for lead in leads:
        if lead.get("client_id"):
            process = await db.processes.find_one(
                {"id": lead["client_id"]},
                {"client_name": 1, "_id": 0}
            )
            if process:
                lead["client_name"] = process.get("client_name")
    
    return leads


@router.get("/by-status")
async def get_leads_by_status(user: dict = Depends(get_current_user)):
    """Obter leads agrupados por status (para Kanban)."""
    leads = await db.property_leads.find({}, {"_id": 0}).to_list(length=500)
    
    # Enriquecer com nome do cliente
    for lead in leads:
        if lead.get("client_id"):
            process = await db.processes.find_one(
                {"id": lead["client_id"]},
                {"client_name": 1, "_id": 0}
            )
            if process:
                lead["client_name"] = process.get("client_name")
    
    # Agrupar por status
    grouped = {status.value: [] for status in LeadStatus}
    for lead in leads:
        status = lead.get("status", LeadStatus.NOVO.value)
        if status in grouped:
            grouped[status].append(lead)
    
    return grouped


@router.post("/extract-url")
async def extract_url_data(
    url: str,
    user: dict = Depends(get_current_user)
):
    """Extrair dados de um URL de anúncio de imóvel."""
    if not url:
        raise HTTPException(status_code=400, detail="URL é obrigatório")
    
    # Validar URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    logger.info(f"Extraindo dados de: {url}")
    
    scraped_data = await extract_property_data(url)
    
    return {
        "success": True,
        "data": scraped_data.model_dump(),
        "message": f"Dados extraídos de {scraped_data.source}"
    }


@router.post("", response_model=PropertyLead)
async def create_lead(
    lead_data: PropertyLeadCreate,
    user: dict = Depends(get_current_user)
):
    """Criar um novo lead de imóvel."""
    # Verificar se já existe lead com o mesmo URL
    existing = await db.property_leads.find_one({"url": lead_data.url})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Já existe um lead com este URL"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    lead = PropertyLead(
        id=str(uuid.uuid4()),
        url=lead_data.url,
        title=lead_data.title,
        price=lead_data.price,
        location=lead_data.location,
        typology=lead_data.typology,
        area=lead_data.area,
        photo_url=lead_data.photo_url,
        consultant=lead_data.consultant,
        client_id=lead_data.client_id,
        notes=lead_data.notes,
        status=LeadStatus.NOVO,
        history=[
            LeadHistory(
                timestamp=now,
                event="Lead criado",
                user=user.get("email")
            )
        ],
        created_at=now,
        updated_at=now,
        created_by=user.get("email")
    )
    
    await db.property_leads.insert_one(lead.model_dump())
    
    logger.info(f"Lead criado: {lead.id} por {user.get('email')}")
    
    return lead


@router.get("/{lead_id}", response_model=PropertyLead)
async def get_lead(
    lead_id: str,
    user: dict = Depends(get_current_user)
):
    """Obter um lead específico."""
    lead = await db.property_leads.find_one({"id": lead_id}, {"_id": 0})
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    # Enriquecer com nome do cliente
    if lead.get("client_id"):
        process = await db.processes.find_one(
            {"id": lead["client_id"]},
            {"client_name": 1, "_id": 0}
        )
        if process:
            lead["client_name"] = process.get("client_name")
    
    return lead


@router.patch("/{lead_id}", response_model=PropertyLead)
async def update_lead(
    lead_id: str,
    update_data: PropertyLeadUpdate,
    user: dict = Depends(get_current_user)
):
    """Actualizar um lead."""
    lead = await db.property_leads.find_one({"id": lead_id})
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Preparar actualização
    update_dict = update_data.model_dump(exclude_none=True)
    update_dict["updated_at"] = now
    
    # Adicionar ao histórico se mudou de status
    if "status" in update_dict and update_dict["status"] != lead.get("status"):
        history_entry = LeadHistory(
            timestamp=now,
            event=f"Status alterado para {update_dict['status']}",
            user=user.get("email")
        )
        await db.property_leads.update_one(
            {"id": lead_id},
            {"$push": {"history": history_entry.model_dump()}}
        )
    
    # Aplicar actualização
    await db.property_leads.update_one(
        {"id": lead_id},
        {"$set": update_dict}
    )
    
    # Retornar lead actualizado
    updated_lead = await db.property_leads.find_one({"id": lead_id}, {"_id": 0})
    
    return updated_lead


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: str,
    status: LeadStatus,
    user: dict = Depends(get_current_user)
):
    """Actualizar apenas o status de um lead (para drag & drop)."""
    lead = await db.property_leads.find_one({"id": lead_id})
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Adicionar ao histórico
    history_entry = LeadHistory(
        timestamp=now,
        event=f"Status alterado para {status.value}",
        user=user.get("email")
    )
    
    await db.property_leads.update_one(
        {"id": lead_id},
        {
            "$set": {"status": status.value, "updated_at": now},
            "$push": {"history": history_entry.model_dump()}
        }
    )
    
    return {"success": True, "status": status.value}


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Eliminar um lead (apenas admin/CEO)."""
    result = await db.property_leads.delete_one({"id": lead_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    logger.info(f"Lead {lead_id} eliminado por {user.get('email')}")
    
    return {"success": True, "message": "Lead eliminado"}


@router.post("/{lead_id}/associate-client")
async def associate_client(
    lead_id: str,
    client_id: str,
    user: dict = Depends(get_current_user)
):
    """Associar um lead a um cliente/processo."""
    # Verificar se lead existe
    lead = await db.property_leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    # Verificar se cliente existe
    process = await db.processes.find_one({"id": client_id})
    if not process:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Actualizar lead
    await db.property_leads.update_one(
        {"id": lead_id},
        {
            "$set": {"client_id": client_id, "updated_at": now},
            "$push": {
                "history": LeadHistory(
                    timestamp=now,
                    event=f"Associado ao cliente {process.get('client_name')}",
                    user=user.get("email")
                ).model_dump()
            }
        }
    )
    
    return {
        "success": True,
        "message": f"Lead associado a {process.get('client_name')}"
    }
