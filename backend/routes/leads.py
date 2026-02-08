"""
Rotas para gestão de Leads de Imóveis
"""
import uuid
import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from database import db
from models.lead import (
    PropertyLead, PropertyLeadCreate, PropertyLeadUpdate,
    LeadStatus, LeadHistory, ConsultantInfo
)
# CORRECÇÃO 1: Importar do scraper.py (o novo) e não do property_scraper.py
from services.scraper import scrape_property_url
from services.auth import get_current_user, require_roles
from models.auth import UserRole

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
        query["status"] = status.value
    if client_id:
        query["client_id"] = client_id
    
    # Busca leads e exclui o _id do mongo
    leads = await db.property_leads.find(query, {"_id": 0}).to_list(length=500)
    
    # Enriquecer com nome do cliente (se existir)
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
    """Obter leads agrupados por status (para o Kanban)."""
    leads = await db.property_leads.find({}, {"_id": 0}).to_list(length=500)
    
    # Inicializar grupos
    grouped = {status.value: [] for status in LeadStatus}
    
    for lead in leads:
        # Enriquecer nome do cliente
        if lead.get("client_id"):
            process = await db.processes.find_one({"id": lead["client_id"]}, {"client_name": 1})
            if process:
                lead["client_name"] = process.get("client_name")
        
        # Agrupar
        status = lead.get("status", LeadStatus.NOVO.value)
        if status in grouped:
            grouped[status].append(lead)
        else:
            grouped[LeadStatus.NOVO.value].append(lead)
    
    return grouped

@router.post("/extract-url")
async def extract_url_data(
    payload: Dict[str, str], # Recebe JSON { "url": "..." }
    user: dict = Depends(get_current_user)
):
    """
    Extrair dados de um URL usando o Deep Scraper.
    """
    url = payload.get("url")
    if not url:
        # Tentar ler da query string se falhar no body (compatibilidade)
        raise HTTPException(status_code=400, detail="URL é obrigatório")
    
    # Adicionar https se faltar
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    logger.info(f"A iniciar Deep Scraping de: {url}")
    
    try:
        # CORRECÇÃO 2: Usar a função do scraper novo
        raw_data = await scrape_property_url(url)
        
        # CORRECÇÃO 3: Mapeamento de dados (Scraper -> Modelo)
        # O scraper devolve 'url_origem', mas o modelo ConsultantInfo usa 'source_url'
        consultant_data = None
        if raw_data.get('consultor'):
            c = raw_data['consultor']
            consultant_data = {
                "name": c.get('nome'),
                "phone": c.get('telefone'),
                "email": c.get('email'),
                "agency_name": c.get('agencia'),
                "source_url": c.get('url_origem') # Mapear campo
            }

        cleaned_data = {
            "url": url,
            "title": raw_data.get('titulo'),
            "price": raw_data.get('preco'),
            "location": raw_data.get('localizacao'),
            "typology": raw_data.get('tipologia'),
            "area": raw_data.get('area'),
            "photo_url": raw_data.get('foto_principal'),
            "consultant": consultant_data,
            "source": raw_data.get('fonte', 'auto')
        }
        
        return {
            "success": True,
            "data": cleaned_data,
            "message": "Dados extraídos com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro no scraping: {e}")
        # Não falhar completamente, permitir preenchimento manual
        return {
            "success": False, 
            "message": f"Não foi possível extrair dados automáticos: {str(e)}",
            "data": {"url": url}
        }

@router.post("", response_model=PropertyLead)
async def create_lead(
    lead_data: PropertyLeadCreate,
    user: dict = Depends(get_current_user)
):
    """Criar um novo lead na base de dados."""
    # Verificar duplicados
    existing = await db.property_leads.find_one({"url": lead_data.url})
    if existing:
        raise HTTPException(status_code=400, detail="Já existe um lead com este URL")
    
    now = datetime.now(timezone.utc).isoformat()
    
    lead_dict = lead_data.model_dump()
    lead_dict["id"] = str(uuid.uuid4())
    lead_dict["status"] = LeadStatus.NOVO.value
    lead_dict["created_at"] = now
    lead_dict["updated_at"] = now
    lead_dict["created_by"] = user.get("email")
    lead_dict["history"] = [{
        "timestamp": now,
        "event": "Lead criado",
        "user": user.get("email")
    }]
    
    await db.property_leads.insert_one(lead_dict)
    return lead_dict

@router.patch("/{lead_id}", response_model=PropertyLead)
async def update_lead(
    lead_id: str,
    update_data: PropertyLeadUpdate,
    user: dict = Depends(get_current_user)
):
    """Atualizar dados de um lead."""
    lead = await db.property_leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    update_dict = update_data.model_dump(exclude_none=True)
    update_dict["updated_at"] = now
    
    # Registar mudança de estado no histórico
    if "status" in update_dict and update_dict["status"] != lead.get("status"):
        update_dict.setdefault("history", lead.get("history", []))
        update_dict["history"].append({
            "timestamp": now,
            "event": f"Status alterado para {update_dict['status']}",
            "user": user.get("email")
        })

    await db.property_leads.update_one({"id": lead_id}, {"$set": update_dict})
    
    return await db.property_leads.find_one({"id": lead_id}, {"_id": 0})

@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: str,
    status: str, 
    user: dict = Depends(get_current_user)
):
    """Endpoint rápido para mudar estado (Drag & Drop)."""
    lead = await db.property_leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    # Validar se o status existe no Enum
    valid_statuses = [s.value for s in LeadStatus]
    if status not in valid_statuses:
         raise HTTPException(status_code=400, detail="Estado inválido")

    now = datetime.now(timezone.utc).isoformat()
    
    await db.property_leads.update_one(
        {"id": lead_id},
        {
            "$set": {"status": status, "updated_at": now},
            "$push": {"history": {
                "timestamp": now,
                "event": f"Status alterado para {status}",
                "user": user.get("email")
            }}
        }
    )
    return {"success": True, "status": status}

@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, user: dict = Depends(get_current_user)):
    """Eliminar lead."""
    result = await db.property_leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return {"success": True}