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
# CORREÇÃO: Importar do novo scraper.py
from services.scraper import scrape_property_url
from services.auth import get_current_user, require_roles
from models.auth import UserRole

router = APIRouter(prefix="/leads", tags=["Property Leads"])
logger = logging.getLogger(__name__)

@router.get("", response_model=List[PropertyLead])
async def list_leads(
    status: Optional[LeadStatus] = None,
    client_id: Optional[str] = None,
    consultor_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Listar todos os leads de imóveis com filtros opcionais."""
    query = {}
    
    if status:
        query["status"] = status.value
    if client_id:
        query["client_id"] = client_id
    if consultor_id:
        query["created_by_id"] = consultor_id
    
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
async def get_leads_by_status(
    consultor_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Obter leads agrupados por status (para o Kanban).
    Suporta filtros por consultor e por estado.
    """
    query = {}
    
    if consultor_id:
        query["created_by_id"] = consultor_id
    
    if status_filter and status_filter != "all":
        query["status"] = status_filter
    
    leads = await db.property_leads.find(query, {"_id": 0}).to_list(length=500)
    
    # Inicializar grupos
    grouped = {status.value: [] for status in LeadStatus}
    
    for lead in leads:
        # Enriquecer nome do cliente
        if lead.get("client_id"):
            process = await db.processes.find_one({"id": lead["client_id"]}, {"client_name": 1})
            if process:
                lead["client_name"] = process.get("client_name")
        
        # Calcular dias desde criação
        if lead.get("created_at"):
            try:
                from datetime import datetime, timezone
                created = datetime.fromisoformat(lead["created_at"].replace('Z', '+00:00'))
                days_old = (datetime.now(timezone.utc) - created).days
                lead["days_old"] = days_old
                lead["is_stale"] = days_old > 7 and lead.get("status") == LeadStatus.NOVO.value
            except:
                lead["days_old"] = 0
                lead["is_stale"] = False
        
        # Agrupar
        lead_status = lead.get("status", LeadStatus.NOVO.value)
        if lead_status in grouped:
            grouped[lead_status].append(lead)
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
        # CORREÇÃO: Usar a função do scraper novo
        raw_data = await scrape_property_url(url)
        
        # CORREÇÃO: Mapeamento de dados (Scraper -> Modelo)
        # O scraper devolve 'url_origem', mas o modelo ConsultantInfo usa 'source_url'
        consultant_data = None
        # raw_data é um dict, não um objeto, por causa do to_dict() no scraper
        raw_consultor = raw_data.get('consultor')
        
        if raw_consultor:
            consultant_data = {
                "name": raw_consultor.get('nome'),
                "phone": raw_consultor.get('telefone'),
                "email": raw_consultor.get('email'),
                "agency_name": raw_consultor.get('agencia'),
                "source_url": raw_consultor.get('url_origem') # Mapear campo
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
        # Garantir que o histórico existe
        history = lead.get("history", [])
        history.append({
            "timestamp": now,
            "event": f"Status alterado para {update_dict['status']}",
            "user": user.get("email")
        })
        update_dict["history"] = history

    await db.property_leads.update_one({"id": lead_id}, {"$set": update_dict})
    
    # Retornar objeto atualizado (sem _id)
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
    # status vem como query param string, validar contra os valores do enum
    valid_statuses = [s.value for s in LeadStatus]
    if status not in valid_statuses:
         raise HTTPException(status_code=400, detail="Estado inválido")

    now = datetime.now(timezone.utc).isoformat()
    
    # Preparar entrada de histórico
    history_entry = {
        "timestamp": now,
        "event": f"Status alterado para {status}",
        "user": user.get("email")
    }

    await db.property_leads.update_one(
        {"id": lead_id},
        {
            "$set": {"status": status, "updated_at": now},
            "$push": {"history": history_entry}
        }
    )
    return {"success": True, "status": status}


@router.post("/{lead_id}/refresh")
async def refresh_lead_price(
    lead_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Verificar se o preço do lead mudou visitando o URL novamente.
    Se mudou, actualiza a DB e adiciona entrada ao histórico.
    """
    # Buscar lead
    lead = await db.property_leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    url = lead.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Lead não tem URL associado")
    
    old_price = lead.get("price")
    
    try:
        # Fazer scraping novamente
        scraped_data = await scrape_property_url(url)
        
        if scraped_data.get("error"):
            return {
                "success": False,
                "message": f"Erro ao verificar: {scraped_data.get('error')}",
                "old_price": old_price,
                "new_price": None,
                "price_changed": False
            }
        
        new_price = scraped_data.get("preco")
        now = datetime.now(timezone.utc).isoformat()
        
        # Verificar se o preço mudou
        price_changed = new_price is not None and new_price != old_price
        
        update_fields = {
            "updated_at": now,
            "last_checked_at": now
        }
        
        history_entry = {
            "timestamp": now,
            "event": "Preço verificado",
            "user": user.get("email")
        }
        
        if price_changed:
            update_fields["price"] = new_price
            history_entry["event"] = f"Preço alterado de {old_price or 'N/D'}€ para {new_price}€"
            logger.info(f"Lead {lead_id}: Preço alterado de {old_price} para {new_price}")
        
        # Também actualizar outros campos se disponíveis
        if scraped_data.get("titulo"):
            update_fields["title"] = scraped_data.get("titulo")
        if scraped_data.get("localizacao"):
            update_fields["location"] = scraped_data.get("localizacao")
        
        await db.property_leads.update_one(
            {"id": lead_id},
            {
                "$set": update_fields,
                "$push": {"history": history_entry}
            }
        )
        
        return {
            "success": True,
            "message": "Preço alterado" if price_changed else "Preço sem alteração",
            "old_price": old_price,
            "new_price": new_price,
            "price_changed": price_changed
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar preço do lead {lead_id}: {str(e)}")
        return {
            "success": False,
            "message": f"Erro ao verificar preço: {str(e)}",
            "old_price": old_price,
            "new_price": None,
            "price_changed": False
        }


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, user: dict = Depends(get_current_user)):
    """Eliminar lead."""
    result = await db.property_leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return {"success": True}

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
                "history": {
                    "timestamp": now,
                    "event": f"Associado ao cliente {process.get('client_name')}",
                    "user": user.get("email")
                }
            }
        }
    )
    
    return {
        "success": True,
        "message": f"Lead associado a {process.get('client_name')}"
    }