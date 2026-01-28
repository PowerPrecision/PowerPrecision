"""
====================================================================
ROTAS DE GESTÃO DE DOCUMENTOS - CREDITOIMO
====================================================================
Sistema de rastreamento e gestão de validade de documentos.

Este módulo permite:
- Criar registos de validade de documentos
- Consultar documentos por processo ou utilizador
- Alertar sobre documentos próximos a expirar (60 dias)
- Atualizar e eliminar registos de documentos

INTEGRAÇÃO COM CALENDÁRIO:
Os documentos próximos a expirar aparecem automaticamente no calendário
como eventos de alerta, permitindo acompanhamento proativo.

Autor: CreditoIMO Development Team
====================================================================
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from database import db
from models.auth import UserRole
from models.document import DocumentExpiryCreate, DocumentExpiryUpdate, DocumentExpiryResponse
from services.auth import get_current_user, require_roles


router = APIRouter(prefix="/documents", tags=["Document Management"])


# ====================================================================
# CONSTANTE: DIAS PARA ALERTA DE EXPIRAÇÃO
# ====================================================================
EXPIRY_WARNING_DAYS = 60  # Documentos a expirar nos próximos 60 dias


@router.post("/expiry", response_model=DocumentExpiryResponse)
async def create_document_expiry(
    data: DocumentExpiryCreate,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CONSULTOR, UserRole.MEDIADOR]))
):
    """
    Criar um novo registo de validade de documento para um processo.
    
    Este endpoint permite registar a data de validade de documentos
    associados a um processo de crédito ou imobiliário.
    
    Args:
        data: Dados do documento (tipo, nome, data de validade)
        user: Utilizador autenticado (Admin, Consultor ou Mediador)
    
    Returns:
        DocumentExpiryResponse: Registo criado
    """
    # Verificar se o processo existe
    process = await db.processes.find_one({"id": data.process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": doc_id,
        "process_id": data.process_id,
        "document_type": data.document_type,
        "document_name": data.document_name,
        "expiry_date": data.expiry_date,
        "notes": data.notes,
        "created_at": now,
        "created_by": user["id"]
    }
    
    await db.document_expiries.insert_one(doc)
    
    return DocumentExpiryResponse(**{k: v for k, v in doc.items() if k != "_id"})


@router.get("/expiry", response_model=List[DocumentExpiryResponse])
async def get_document_expiries(
    process_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Obter registos de validade de documentos.
    
    Permite filtrar por processo ou obtém todos os documentos
    acessíveis ao utilizador baseado no seu papel.
    
    Args:
        process_id: ID do processo (opcional)
        user: Utilizador autenticado
    
    Returns:
        Lista de registos de documentos
    """
    query = {}
    
    if process_id:
        query["process_id"] = process_id
    elif user["role"] == UserRole.CONSULTOR:
        # Obter processos atribuídos a este consultor
        processes = await db.processes.find(
            {"assigned_consultor_id": user["id"]}, 
            {"id": 1, "_id": 0}
        ).to_list(1000)
        process_ids = [p["id"] for p in processes]
        query["process_id"] = {"$in": process_ids}
    elif user["role"] == UserRole.MEDIADOR:
        # Obter processos atribuídos a este mediador/intermediário
        processes = await db.processes.find(
            {"assigned_mediador_id": user["id"]}, 
            {"id": 1, "_id": 0}
        ).to_list(1000)
        process_ids = [p["id"] for p in processes]
        query["process_id"] = {"$in": process_ids}
    
    docs = await db.document_expiries.find(query, {"_id": 0}).to_list(1000)
    return [DocumentExpiryResponse(**d) for d in docs]


@router.get("/expiry/upcoming")
async def get_upcoming_expiries(
    days: int = EXPIRY_WARNING_DAYS,
    user: dict = Depends(get_current_user)
):
    """
    Obter documentos que expiram nos próximos N dias.
    
    Por defeito, retorna documentos a expirar em 60 dias.
    EXCLUI processos concluídos e desistências.
    Estes documentos também aparecem no calendário como alertas.
    
    Args:
        days: Número de dias para o horizonte de alerta (default: 60)
        user: Utilizador autenticado
    
    Returns:
        Lista de documentos a expirar com informação do cliente
    """
    today = datetime.now(timezone.utc).date()
    future_date = today + timedelta(days=days)
    
    # Estados a EXCLUIR da análise de documentos
    excluded_statuses = ["concluido", "desistencia", "desistência"]
    
    query = {
        "expiry_date": {
            "$gte": today.isoformat(),
            "$lte": future_date.isoformat()
        }
    }
    
    # Filtrar por papel do utilizador
    user_role = user["role"]
    
    if user_role in [UserRole.ADMIN, UserRole.CEO]:
        # Admin e CEO vêem todos os documentos
        pass
    elif user_role == UserRole.CONSULTOR:
        # Consultor vê documentos dos seus processos
        processes = await db.processes.find(
            {"$or": [
                {"assigned_consultor_id": user["id"]},
                {"consultor_id": user["id"]}
            ]}, 
            {"id": 1, "_id": 0}
        ).to_list(1000)
        process_ids = [p["id"] for p in processes]
        if process_ids:
            query["process_id"] = {"$in": process_ids}
        else:
            return []  # Sem processos, sem documentos
    elif user_role in [UserRole.MEDIADOR, UserRole.INTERMEDIARIO]:
        # Intermediário vê documentos dos seus processos
        processes = await db.processes.find(
            {"$or": [
                {"assigned_mediador_id": user["id"]},
                {"intermediario_id": user["id"]}
            ]}, 
            {"id": 1, "_id": 0}
        ).to_list(1000)
        process_ids = [p["id"] for p in processes]
        if process_ids:
            query["process_id"] = {"$in": process_ids}
        else:
            return []
    elif user_role == UserRole.DIRETOR:
        # Diretor vê documentos de ambos os tipos de processos
        processes = await db.processes.find(
            {"$or": [
                {"assigned_consultor_id": user["id"]},
                {"consultor_id": user["id"]},
                {"assigned_mediador_id": user["id"]},
                {"intermediario_id": user["id"]}
            ]}, 
            {"id": 1, "_id": 0}
        ).to_list(1000)
        process_ids = [p["id"] for p in processes]
        if process_ids:
            query["process_id"] = {"$in": process_ids}
        else:
            return []
    elif user_role == UserRole.CLIENTE:
        # Cliente vê documentos dos próprios processos
        processes = await db.processes.find(
            {"client_id": user["id"]}, 
            {"id": 1, "_id": 0}
        ).to_list(1000)
        process_ids = [p["id"] for p in processes]
        if process_ids:
            query["process_id"] = {"$in": process_ids}
        else:
            return []
    
    docs = await db.document_expiries.find(query, {"_id": 0}).sort("expiry_date", 1).to_list(1000)
    
    # Enriquecer com informação do processo e filtrar por estado
    result = []
    for doc in docs:
        process = await db.processes.find_one({"id": doc["process_id"]}, {"_id": 0})
        if process:
            # EXCLUIR processos concluídos e desistências
            process_status = process.get("status", "").lower()
            if process_status in excluded_statuses:
                continue
            
            # Calcular dias até expirar
            expiry = datetime.strptime(doc["expiry_date"], "%Y-%m-%d").date()
            days_until = (expiry - today).days
            
            result.append({
                **doc,
                "client_name": process.get("client_name"),
                "client_email": process.get("client_email"),
                "client_phone": process.get("client_phone"),
                "process_status": process.get("status"),
                "days_until_expiry": days_until,
                "urgency": "critical" if days_until <= 7 else "warning" if days_until <= 30 else "normal"
            })
    
    return result


@router.get("/expiry/calendar")
async def get_expiry_calendar_events(
    user: dict = Depends(get_current_user)
):
    """
    Obter eventos de expiração de documentos para o calendário.
    
    Retorna documentos a expirar nos próximos 60 dias formatados
    como eventos de calendário para fácil integração.
    
    Returns:
        Lista de eventos formatados para calendário
    """
    # Obter documentos a expirar
    upcoming = await get_upcoming_expiries(days=EXPIRY_WARNING_DAYS, user=user)
    
    # Formatar como eventos de calendário
    events = []
    for doc in upcoming:
        urgency_colors = {
            "critical": "#EF4444",   # Vermelho
            "warning": "#F59E0B",    # Âmbar
            "normal": "#3B82F6"      # Azul
        }
        
        events.append({
            "id": f"doc-expiry-{doc['id']}",
            "title": f"📄 {doc['document_name']} - {doc['client_name']}",
            "description": f"Documento expira em {doc['days_until_expiry']} dias",
            "date": doc["expiry_date"],
            "type": "document_expiry",
            "priority": doc["urgency"],
            "color": urgency_colors.get(doc["urgency"], "#3B82F6"),
            "process_id": doc["process_id"],
            "document_id": doc["id"]
        })
    
    return events


@router.put("/expiry/{doc_id}", response_model=DocumentExpiryResponse)
async def update_document_expiry(
    doc_id: str,
    data: DocumentExpiryUpdate,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CONSULTOR, UserRole.MEDIADOR]))
):
    """
    Atualizar um registo de validade de documento.
    
    Args:
        doc_id: ID do registo a atualizar
        data: Campos a atualizar
        user: Utilizador autenticado
    
    Returns:
        Registo atualizado
    """
    doc = await db.document_expiries.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    
    update_data = {}
    if data.document_name is not None:
        update_data["document_name"] = data.document_name
    if data.expiry_date is not None:
        update_data["expiry_date"] = data.expiry_date
    if data.notes is not None:
        update_data["notes"] = data.notes
    
    if update_data:
        await db.document_expiries.update_one({"id": doc_id}, {"$set": update_data})
    
    updated = await db.document_expiries.find_one({"id": doc_id}, {"_id": 0})
    return DocumentExpiryResponse(**updated)


@router.delete("/expiry/{doc_id}")
async def delete_document_expiry(
    doc_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CONSULTOR, UserRole.MEDIADOR]))
):
    """
    Eliminar um registo de validade de documento.
    
    Args:
        doc_id: ID do registo a eliminar
        user: Utilizador autenticado
    
    Returns:
        Mensagem de confirmação
    """
    result = await db.document_expiries.delete_one({"id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    return {"message": "Registo eliminado com sucesso"}


# ====================================================================
# TIPOS DE DOCUMENTO SUPORTADOS
# ====================================================================
# Lista de tipos de documentos comummente utilizados em processos
# de crédito habitação e transações imobiliárias em Portugal

DOCUMENT_TYPES = [
    {"type": "cc", "name": "Cartão de Cidadão", "icon": "id-card", "validity_years": 5},
    {"type": "passaporte", "name": "Passaporte", "icon": "passport", "validity_years": 5},
    {"type": "carta_conducao", "name": "Carta de Condução", "icon": "car", "validity_years": 15},
    {"type": "contrato_trabalho", "name": "Contrato de Trabalho", "icon": "file-text", "validity_years": None},
    {"type": "recibos_vencimento", "name": "Recibos de Vencimento", "icon": "file-text", "validity_months": 3},
    {"type": "declaracao_irs", "name": "Declaração de IRS", "icon": "file-text", "validity_years": 1},
    {"type": "certidao_predial", "name": "Certidão Predial", "icon": "home", "validity_months": 6},
    {"type": "caderneta_predial", "name": "Caderneta Predial", "icon": "home", "validity_years": 1},
    {"type": "licenca_utilizacao", "name": "Licença de Utilização", "icon": "home", "validity_years": None},
    {"type": "ficha_tecnica", "name": "Ficha Técnica Habitação", "icon": "home", "validity_years": None},
    {"type": "comprovativo_morada", "name": "Comprovativo de Morada", "icon": "home", "validity_months": 3},
    {"type": "certidao_nascimento", "name": "Certidão de Nascimento", "icon": "file-text", "validity_months": 6},
    {"type": "certidao_casamento", "name": "Certidão de Casamento", "icon": "file-text", "validity_months": 6},
    {"type": "outro", "name": "Outro", "icon": "file", "validity_years": None},
]


@router.get("/types")
async def get_document_types(user: dict = Depends(get_current_user)):
    """
    Obter lista de tipos de documentos suportados.
    
    Retorna todos os tipos de documentos que podem ser registados,
    incluindo informação sobre validade típica.
    
    Returns:
        Lista de tipos de documentos
    """
    return DOCUMENT_TYPES
