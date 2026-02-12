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


async def _log_system_error(
    error_type: str,
    message: str,
    details: dict = None,
    severity: str = "warning"
):
    """
    Regista um erro no sistema para o admin visualizar.
    
    Args:
        error_type: Tipo de erro (scraper_error, api_error, validation_error, etc.)
        message: Mensagem descritiva do erro
        details: Detalhes adicionais (dict)
        severity: Nível (info, warning, error, critical)
    """
    try:
        error_log = {
            "id": str(uuid.uuid4()),
            "type": error_type,
            "message": message,
            "details": details or {},
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "resolved": False
        }
        await db.system_error_logs.insert_one(error_log)
    except Exception as e:
        logger.error(f"Falha ao registar erro no sistema: {e}")

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


@router.get("/consultores")
async def get_consultores_for_filter(user: dict = Depends(get_current_user)):
    """
    Obter lista de consultores para os filtros do Kanban.
    Retorna utilizadores com role consultor, diretor ou admin.
    """
    consultores = await db.users.find(
        {"role": {"$in": ["consultor", "diretor", "admin", "administrativo"]}},
        {"_id": 0, "id": 1, "name": 1, "email": 1}
    ).to_list(length=100)
    
    return consultores


@router.post("/extract-url")
async def extract_url_data(
    payload: Dict[str, str], # Recebe JSON { "url": "..." }
    user: dict = Depends(get_current_user)
):
    """
    Extrair dados de um URL usando o Deep Scraper.
    
    Melhorias (Item 6):
    - Navegação automática ao link da agência se não encontrar telefone
    - Extracção de referência do anúncio
    - Mais campos de propriedade (certificado energético, ano construção, estado)
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
        # Usar scraper híbrido
        raw_data = await scrape_property_url(url)
        
        # Verificar se houve erro
        if raw_data.get("error"):
            logger.warning(f"Scraper retornou erro: {raw_data.get('error')}")
            # Log para admin
            await _log_system_error(
                error_type="scraper_error",
                message=f"Erro ao extrair dados de {url}: {raw_data.get('error')}",
                details={"url": url, "error": raw_data.get("error")}
            )
            return {
                "success": False,
                "message": f"Erro ao extrair: {raw_data.get('error')}",
                "data": {"url": url}
            }
        
        # Mapear dados do scraper para o formato esperado pelo lead
        consultant_data = None
        if raw_data.get("agente_nome") or raw_data.get("agente_telefone") or raw_data.get("agente_email"):
            consultant_data = {
                "name": raw_data.get("agente_nome"),
                "phone": raw_data.get("agente_telefone"),
                "email": raw_data.get("agente_email"),
                "agency_name": raw_data.get("agencia_nome"),
                "source_url": raw_data.get("url")
            }
        
        # Também verificar campos antigos do scraper (compatibilidade)
        if not consultant_data and raw_data.get("consultor"):
            raw_consultor = raw_data.get("consultor")
            consultant_data = {
                "name": raw_consultor.get("nome"),
                "phone": raw_consultor.get("telefone"),
                "email": raw_consultor.get("email"),
                "agency_name": raw_consultor.get("agencia"),
                "source_url": raw_consultor.get("url_origem")
            }

        # === MELHORIAS Item 6 ===
        cleaned_data = {
            "url": url,
            "title": raw_data.get("titulo"),
            "price": raw_data.get("preco"),
            "location": raw_data.get("localizacao"),
            "typology": raw_data.get("tipologia"),
            "area": raw_data.get("area"),
            "bedrooms": raw_data.get("quartos"),
            "bathrooms": raw_data.get("casas_banho"),
            "description": raw_data.get("descricao"),
            "photo_url": raw_data.get("foto_principal"),
            "consultant": consultant_data,
            "source": raw_data.get("fonte", raw_data.get("_parser", "auto")),
            "_extracted_by": raw_data.get("_extracted_by"),
            # Novos campos (Item 6)
            "reference": raw_data.get("referencia") or raw_data.get("reference"),
            "energy_certificate": raw_data.get("certificado_energetico"),
            "year_built": raw_data.get("ano_construcao"),
            "condition": raw_data.get("estado"),
            "agency_link": raw_data.get("agency_link"),
            "_raw_fields": list(raw_data.keys())  # Para debug
        }
        
        # Verificar se extraiu dados úteis
        has_useful_data = cleaned_data.get("title") or cleaned_data.get("price") or cleaned_data.get("location")
        
        if not has_useful_data:
            logger.warning(f"Scraper não extraiu dados úteis de {url}")
            await _log_system_error(
                error_type="scraper_no_data",
                message=f"Não foi possível extrair dados de {url}",
                details={"url": url, "raw_keys": list(raw_data.keys()), "extracted_by": raw_data.get("_extracted_by")}
            )
        
        return {
            "success": has_useful_data,
            "data": cleaned_data,
            "message": "Dados extraídos com sucesso" if has_useful_data else "Poucos dados extraídos - preencha manualmente"
        }
        
    except Exception as e:
        logger.error(f"Erro no scraping: {e}")
        # Log para admin
        await _log_system_error(
            error_type="scraper_exception",
            message=f"Excepção ao extrair dados de {url}",
            details={"url": url, "error": str(e), "error_type": type(e).__name__}
        )
        return {
            "success": False, 
            "message": f"Não foi possível extrair dados automáticos: {str(e)}",
            "data": {"url": url}
        }


@router.post("/from-url")
async def create_lead_from_url(
    payload: Dict[str, str],
    user: dict = Depends(get_current_user)
):
    """
    Extrair dados de um URL e criar um lead automaticamente.
    Combina extração de dados e criação do lead num único passo.
    """
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL é obrigatório")
    
    # Adicionar https se faltar
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    # Verificar duplicados
    existing = await db.property_leads.find_one({"url": url})
    if existing:
        return {
            "success": False,
            "message": "Já existe um lead com este URL",
            "lead": existing
        }
    
    logger.info(f"A criar lead de: {url}")
    
    try:
        # Extrair dados usando o scraper
        raw_data = await scrape_property_url(url)
        
        # Verificar se houve erro no scraper
        if raw_data.get("error"):
            await _log_system_error(
                error_type="scraper_error",
                message=f"Erro ao extrair dados de {url}: {raw_data.get('error')}",
                details={"url": url, "error": raw_data.get("error")},
                severity="warning"
            )
            return {
                "success": False,
                "message": f"Erro ao extrair: {raw_data.get('error')}. Pode criar o lead manualmente.",
                "data": {"url": url}
            }
        
        # Mapear dados do scraper para o formato do lead
        # O scraper retorna: titulo, preco, localizacao, tipologia, area, agente_nome, agente_telefone, agente_email, agencia_nome
        consultant_data = None
        if raw_data.get("agente_nome") or raw_data.get("agente_telefone") or raw_data.get("agente_email"):
            consultant_data = {
                "name": raw_data.get("agente_nome"),
                "phone": raw_data.get("agente_telefone"),
                "email": raw_data.get("agente_email"),
                "agency_name": raw_data.get("agencia_nome"),
                "source_url": raw_data.get("url")
            }
        
        # Também verificar campos antigos do scraper (compatibilidade)
        if not consultant_data and raw_data.get("consultor"):
            raw_consultor = raw_data.get("consultor")
            consultant_data = {
                "name": raw_consultor.get("nome"),
                "phone": raw_consultor.get("telefone"),
                "email": raw_consultor.get("email"),
                "agency_name": raw_consultor.get("agencia"),
                "source_url": raw_consultor.get("url_origem")
            }
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Criar o lead com os dados extraídos
        lead_dict = {
            "id": str(uuid.uuid4()),
            "url": url,
            "title": raw_data.get("titulo"),
            "price": raw_data.get("preco"),
            "location": raw_data.get("localizacao"),
            "typology": raw_data.get("tipologia"),
            "area": raw_data.get("area"),
            "bedrooms": raw_data.get("quartos"),
            "bathrooms": raw_data.get("casas_banho"),
            "description": raw_data.get("descricao"),
            "photo_url": raw_data.get("foto_principal"),
            "consultant": consultant_data,
            "source": raw_data.get("fonte", raw_data.get("_parser", "auto")),
            "status": LeadStatus.NOVO.value,
            "created_at": now,
            "updated_at": now,
            "created_by": user.get("email"),
            "created_by_id": user.get("id"),
            "history": [{
                "timestamp": now,
                "event": "Lead criado automaticamente via URL",
                "user": user.get("email")
            }]
        }
        
        # Inserir na base de dados
        await db.property_leads.insert_one(lead_dict)
        
        # Verificar se extraiu dados úteis
        has_useful_data = lead_dict.get("title") or lead_dict.get("price") or lead_dict.get("location")
        
        if not has_useful_data:
            await _log_system_error(
                error_type="scraper_no_data",
                message=f"Lead criado mas com poucos dados de {url}",
                details={"url": url, "lead_id": lead_dict["id"]},
                severity="info"
            )
        
        # Remover _id do MongoDB antes de retornar
        lead_dict.pop("_id", None)
        
        return {
            "success": True,
            "message": "Lead criado com sucesso" if has_useful_data else "Lead criado mas com poucos dados extraídos - edite manualmente",
            "lead": lead_dict
        }
        
    except Exception as e:
        logger.error(f"Erro ao criar lead de URL: {e}")
        await _log_system_error(
            error_type="scraper_exception",
            message=f"Excepção ao criar lead de {url}",
            details={"url": url, "error": str(e), "error_type": type(e).__name__},
            severity="error"
        )
        raise HTTPException(status_code=500, detail=f"Erro ao criar lead: {str(e)}")


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
    lead_dict["created_by_id"] = user.get("id")  # Para filtros por consultor
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