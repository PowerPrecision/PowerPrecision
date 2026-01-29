"""
====================================================================
ROTAS DE GESTÃO DE PROCESSOS - CREDITOIMO
====================================================================
Módulo principal para gestão de processos de crédito habitação
e transações imobiliárias.

FUNCIONALIDADES PRINCIPAIS:
- Criar e atualizar processos de clientes
- Visualização em quadro Kanban
- Movimentação entre fases do workflow
- Atribuição de consultores e intermediários
- Filtros por papel do utilizador

WORKFLOW DE 14 FASES:
1. Clientes em Espera
2. Fase Documental
3. Fase Documental II
4. Enviado ao Bruno
5. Enviado ao Luís
6. Enviado BCP Rui
7. Entradas Precision
8. Fase Bancária
9. Fase de Visitas
10. CH Aprovado
11. Fase de Escritura
12. Escritura Agendada
13. Concluídos
14. Desistências

Autor: CreditoIMO Development Team
====================================================================
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from database import db
from models.auth import UserRole
from models.process import (
    ProcessType, ProcessCreate, ProcessUpdate, ProcessResponse
)
from services.auth import get_current_user, require_roles, require_staff
from services.email import send_email_notification
from services.history import log_history, log_data_changes
from services.alerts import (
    get_process_alerts,
    check_property_documents,
    create_deed_reminder,
    notify_pre_approval_countdown,
    notify_cpcv_or_deed_document_check
)
from services.realtime_notifications import notify_process_status_change
from services.trello import trello_service, status_to_trello_list, build_card_description

logger = logging.getLogger(__name__)


async def get_next_process_number() -> int:
    """Obter o próximo número sequencial para um novo processo."""
    # Buscar o maior process_number existente
    result = await db.processes.find_one(
        {"process_number": {"$exists": True, "$ne": None}},
        {"process_number": 1},
        sort=[("process_number", -1)]
    )
    
    if result and result.get("process_number"):
        return result["process_number"] + 1
    return 1  # Primeiro processo


async def sync_process_to_trello(process: dict):
    """Sincronizar processo com o Trello (nome e descrição do card)."""
    if not process.get("trello_card_id") or not trello_service.api_key:
        return False
    
    try:
        description = build_card_description(process)
        await trello_service.update_card(
            process["trello_card_id"],
            name=process.get("client_name", "Sem nome"),
            desc=description
        )
        logger.info(f"Card {process['trello_card_id']} atualizado no Trello: {process.get('client_name')}")
        return True
    except Exception as e:
        logger.error(f"Erro ao sincronizar com Trello: {e}")
        return False


# ====================================================================
# CONFIGURAÇÃO DO ROUTER
# ====================================================================
router = APIRouter(prefix="/processes", tags=["Processes"])


# ====================================================================
# FUNÇÕES AUXILIARES DE PERMISSÕES
# ====================================================================

def can_view_process(user: dict, process: dict) -> bool:
    """
    Verifica se um utilizador pode visualizar um processo específico.
    
    REGRAS DE ACESSO:
    - Admin/CEO: Acesso a todos os processos
    - Cliente: Apenas o próprio processo
    - Consultor: Processos onde está atribuído como consultor
    - Intermediário: Processos onde está atribuído como intermediário
    - Consultor/Intermediário: Ambos os tipos de atribuição
    
    Args:
        user: Dados do utilizador autenticado
        process: Dados do processo a verificar
    
    Returns:
        bool: True se tem permissão, False caso contrário
    """
    role = user["role"]
    user_id = user["id"]
    
    # Administradores e CEO têm acesso total
    if role == UserRole.ADMIN:
        return True
    if role == UserRole.CEO:
        return True
    
    # Clientes só vêem os próprios processos
    if role == UserRole.CLIENTE:
        return process.get("client_id") == user_id
    
    # Consultores vêem processos atribuídos
    if role == UserRole.CONSULTOR:
        return process.get("assigned_consultor_id") == user_id
    
    # Intermediários vêem processos atribuídos
    if role == UserRole.MEDIADOR:
        return process.get("assigned_mediador_id") == user_id
    
    # Diretor: acesso a ambos os tipos de atribuição (consultor e intermediário)
    if role == UserRole.DIRETOR:
        return (process.get("assigned_consultor_id") == user_id or 
                process.get("assigned_mediador_id") == user_id)
    
    # Administrativo: vê todos os processos (função de apoio)
    if role == UserRole.ADMINISTRATIVO:
        return True
    
    return False


# ====================================================================
# ENDPOINTS DE CRIAÇÃO
# ====================================================================

@router.post("", response_model=ProcessResponse)
async def create_process(data: ProcessCreate, user: dict = Depends(get_current_user)):
    """
    Criar um novo processo.
    
    Este endpoint é utilizado quando um cliente autenticado
    submete um novo pedido de crédito/imobiliário.
    
    NOTA: Para registos públicos (sem autenticação),
    utilize o endpoint /api/public/register
    
    Args:
        data: Dados do processo (tipo, dados pessoais, financeiros)
        user: Utilizador autenticado (deve ser cliente)
    
    Returns:
        ProcessResponse: Processo criado
    
    Raises:
        HTTPException 403: Se não for cliente
    """
    # Apenas clientes podem criar processos por este endpoint
    if user["role"] != UserRole.CLIENTE:
        raise HTTPException(status_code=403, detail="Apenas clientes podem criar processos")
    
    # Obter o primeiro estado do workflow (Clientes em Espera)
    first_status = await db.workflow_statuses.find_one({}, {"_id": 0}, sort=[("order", 1)])
    initial_status = first_status["name"] if first_status else "clientes_espera"
    
    # Gerar ID único e timestamp
    process_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Construir documento do processo
    process_doc = {
        "id": process_id,
        "client_id": user["id"],
        "client_name": user["name"],
        "client_email": user["email"],
        "process_type": data.process_type,
        "status": initial_status,
        "personal_data": data.personal_data.model_dump() if data.personal_data else None,
        "financial_data": data.financial_data.model_dump() if data.financial_data else None,
        "real_estate_data": None,
        "credit_data": None,
        "assigned_consultor_id": None,
        "assigned_mediador_id": None,
        "created_at": now,
        "updated_at": now
    }
    
    # Inserir na base de dados
    await db.processes.insert_one(process_doc)
    
    # Registar no histórico
    await log_history(process_id, user, "Criou processo")
    
    # Notificar administradores e CEO
    staff = await db.users.find(
        {"role": {"$in": [UserRole.ADMIN, UserRole.CEO]}}, 
        {"_id": 0}
    ).to_list(100)
    for s in staff:
        await send_email_notification(
            s["email"],
            "Novo Processo Criado",
            f"O cliente {user['name']} criou um novo processo de {data.process_type}."
        )
    
    return ProcessResponse(**{k: v for k, v in process_doc.items() if k != "_id"})


# ====================================================================
# ENDPOINTS DE LISTAGEM
# ====================================================================

@router.get("", response_model=List[ProcessResponse])
async def get_processes(user: dict = Depends(get_current_user)):
    """
    Listar processos com base no papel do utilizador.
    
    FILTRAGEM AUTOMÁTICA:
    - Admin/CEO: Todos os processos
    - Cliente: Apenas os próprios processos
    - Consultor: Processos atribuídos como consultor
    - Intermediário: Processos atribuídos como intermediário
    - Misto: Ambos os tipos de atribuição
    
    Returns:
        Lista de ProcessResponse
    """
    role = user["role"]
    query = {}
    
    # Construir query baseada no papel
    if role == UserRole.CLIENTE:
        query["client_id"] = user["id"]
    elif role in [UserRole.ADMIN, UserRole.CEO, UserRole.ADMINISTRATIVO]:
        # Admin, CEO e Administrativo vêem todos os processos
        pass
    elif role == UserRole.CONSULTOR:
        query["assigned_consultor_id"] = user["id"]
    elif role in [UserRole.MEDIADOR, UserRole.INTERMEDIARIO]:
        query["assigned_mediador_id"] = user["id"]
    elif role == UserRole.DIRETOR:
        query["$or"] = [
            {"assigned_consultor_id": user["id"]},
            {"assigned_mediador_id": user["id"]}
        ]
    
    processes = await db.processes.find(query, {"_id": 0}).to_list(1000)
    return [ProcessResponse(**p) for p in processes]


@router.get("/kanban")
async def get_kanban_board(user: dict = Depends(require_staff())):
    """
    Get processes organized by status for Kanban board.
    Admin/CEO see all, others see only their assigned processes.
    """
    role = user["role"]
    query = {}
    
    # Filter by role
    if role == UserRole.CONSULTOR:
        query["assigned_consultor_id"] = user["id"]
    elif role in [UserRole.MEDIADOR, UserRole.INTERMEDIARIO]:
        query["assigned_mediador_id"] = user["id"]
    elif role == UserRole.DIRETOR:
        query["$or"] = [
            {"assigned_consultor_id": user["id"]},
            {"assigned_mediador_id": user["id"]}
        ]
    # Admin, CEO e Administrativo see all (no filter)
    
    # Get all workflow statuses ordered
    statuses = await db.workflow_statuses.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    
    # Get processes
    processes = await db.processes.find(query, {"_id": 0}).to_list(1000)
    
    # Get all users for name lookup
    users = await db.users.find({}, {"_id": 0, "id": 1, "name": 1, "role": 1}).to_list(1000)
    user_map = {u["id"]: u for u in users}
    
    # Organize by status
    kanban = []
    for status in statuses:
        status_processes = [p for p in processes if p.get("status") == status["name"]]
        
        # Enrich with user names
        enriched_processes = []
        for p in status_processes:
            consultor = user_map.get(p.get("assigned_consultor_id"), {})
            mediador = user_map.get(p.get("assigned_mediador_id"), {})
            enriched_processes.append({
                **p,
                "consultor_name": consultor.get("name", ""),
                "mediador_name": mediador.get("name", ""),
            })
        
        kanban.append({
            "id": status["id"],
            "name": status["name"],
            "label": status["label"],
            "color": status["color"],
            "order": status["order"],
            "processes": enriched_processes,
            "count": len(enriched_processes)
        })
    
    return {
        "columns": kanban,
        "total_processes": len(processes),
        "user_role": role
    }


@router.put("/kanban/{process_id}/move")
async def move_process_kanban(
    process_id: str,
    new_status: str = Query(..., description="New status name"),
    deed_date: Optional[str] = Query(None, description="Data da escritura (YYYY-MM-DD)"),
    user: dict = Depends(require_staff())
):
    """
    Move a process to a different status column in Kanban.
    
    ALERTAS AUTOMÁTICOS:
    - Ao mover para "ch_aprovado": Inicia countdown de 90 dias, verifica docs do imóvel
    - Ao mover para "escritura_agendada": Cria lembrete 15 dias antes
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Check permission
    if not can_view_process(user, process):
        raise HTTPException(status_code=403, detail="Sem permissão para mover este processo")
    
    # Validate new status
    status_exists = await db.workflow_statuses.find_one({"name": new_status})
    if not status_exists:
        raise HTTPException(status_code=400, detail="Estado inválido")
    
    old_status = process.get("status", "")
    alerts_generated = []
    
    # Update process
    await db.processes.update_one(
        {"id": process_id},
        {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Log history
    await log_history(process_id, user, "Moveu processo", "status", old_status, new_status)
    
    # === ALERTAS AUTOMÁTICOS BASEADOS NA MUDANÇA DE ESTADO ===
    
    # 1. Ao mover para CH Aprovado - Verificar documentos do imóvel
    if new_status in ["ch_aprovado", "fase_escritura"]:
        property_check = await check_property_documents(process)
        if property_check.get("active"):
            alerts_generated.append({
                "type": "property_docs",
                "message": property_check.get("message"),
                "details": property_check.get("details")
            })
    
    # 1.1 Alerta de verificação de documentos para CPCV/Escritura
    if new_status in ["ch_aprovado", "fase_escritura", "escritura_agendada"]:
        await notify_cpcv_or_deed_document_check(process, new_status)
        alerts_generated.append({
            "type": "document_verification_alert",
            "message": "Alerta enviado aos envolvidos para verificação de documentos"
        })
    
    # 2. Ao mover para pré-aprovação - Iniciar countdown de 90 dias
    if new_status == "fase_bancaria" and old_status != "fase_bancaria":
        # Guardar data de aprovação se ainda não existir
        if not process.get("credit_data", {}).get("bank_approval_date"):
            await db.processes.update_one(
                {"id": process_id},
                {"$set": {"credit_data.bank_approval_date": datetime.now().strftime("%Y-%m-%d")}}
            )
        # Notificar sobre o countdown
        updated_process = await db.processes.find_one({"id": process_id}, {"_id": 0})
        await notify_pre_approval_countdown(updated_process)
        alerts_generated.append({
            "type": "countdown_started",
            "message": "Countdown de 90 dias iniciado para pré-aprovação"
        })
    
    # 3. Ao mover para escritura agendada - Criar lembrete 15 dias antes
    if new_status == "escritura_agendada":
        if deed_date:
            deadline_id = await create_deed_reminder(process, deed_date, user)
            if deadline_id:
                alerts_generated.append({
                    "type": "deed_reminder",
                    "message": f"Lembrete de escritura criado para 15 dias antes de {deed_date}"
                })
        else:
            alerts_generated.append({
                "type": "deed_date_needed",
                "message": "Escritura agendada sem data. Defina a data para criar lembrete automático."
            })
    
    # Send email notification if client has email
    if process.get("client_email"):
        status_doc = await db.workflow_statuses.find_one({"name": new_status}, {"_id": 0})
        status_label = status_doc.get("label", new_status) if status_doc else new_status
        await send_email_notification(
            process["client_email"],
            f"Atualização do seu processo",
            f"O estado do seu processo foi atualizado para: {status_label}"
        )
    
    # === CRIAR NOTIFICAÇÃO NA BASE DE DADOS ===
    status_doc = await db.workflow_statuses.find_one({"name": new_status}, {"_id": 0})
    status_label = status_doc.get("label", new_status) if status_doc else new_status
    
    await notify_process_status_change(
        process=process,
        old_status=old_status,
        new_status=new_status,
        new_status_label=status_label,
        changed_by=user
    )
    
    # === SINCRONIZAR COM TRELLO ===
    if process.get("trello_card_id") and trello_service.api_key:
        try:
            trello_list_name = status_to_trello_list(new_status)
            if trello_list_name:
                # Encontrar a lista do Trello pelo nome
                trello_list = await trello_service.get_list_by_name(trello_list_name)
                if trello_list:
                    await trello_service.move_card(process["trello_card_id"], trello_list["id"])
                    logger.info(f"Card {process['trello_card_id']} movido para {trello_list_name} no Trello")
        except Exception as e:
            logger.error(f"Erro ao sincronizar com Trello: {e}")
            # Não falhar a operação por erro no Trello
    
    return {
        "message": "Processo movido com sucesso", 
        "new_status": new_status,
        "alerts": alerts_generated
    }


@router.get("/{process_id}", response_model=ProcessResponse)
async def get_process(process_id: str, user: dict = Depends(get_current_user)):
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    if not can_view_process(user, process):
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    return ProcessResponse(**process)


@router.get("/{process_id}/alerts")
async def get_process_alerts_endpoint(process_id: str, user: dict = Depends(get_current_user)):
    """
    Obter todos os alertas ativos para um processo.
    
    Retorna alertas de:
    - Idade < 35 anos (Apoio ao Estado)
    - Countdown de 90 dias (pré-aprovação)
    - Documentos a expirar em 15 dias
    - Documentos do imóvel em falta
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    if not can_view_process(user, process):
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    alerts = await get_process_alerts(process)
    
    return {
        "process_id": process_id,
        "client_name": process.get("client_name"),
        "alerts": alerts,
        "total": len(alerts),
        "has_critical": any(a.get("priority") == "critical" for a in alerts),
        "has_high": any(a.get("priority") == "high" for a in alerts)
    }


@router.put("/{process_id}", response_model=ProcessResponse)
async def update_process(process_id: str, data: ProcessUpdate, user: dict = Depends(get_current_user)):
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    role = user["role"]
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    valid_statuses = [s["name"] for s in await db.workflow_statuses.find({}, {"name": 1, "_id": 0}).to_list(100)]
    
    # Check role-based permissions
    can_update_personal = role in [UserRole.ADMIN, UserRole.CEO, UserRole.CONSULTOR, UserRole.DIRETOR, UserRole.ADMINISTRATIVO]
    can_update_financial = role in [UserRole.ADMIN, UserRole.CEO, UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.DIRETOR, UserRole.ADMINISTRATIVO]
    can_update_real_estate = UserRole.can_act_as_consultor(role)
    can_update_credit = UserRole.can_act_as_mediador(role)
    can_update_status = role in [UserRole.ADMIN, UserRole.CEO, UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.DIRETOR, UserRole.ADMINISTRATIVO]
    
    if role == UserRole.CLIENTE:
        if process.get("client_id") != user["id"]:
            raise HTTPException(status_code=403, detail="Acesso negado")
        if data.personal_data:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        if data.financial_data:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
    else:
        # Staff updates
        if data.personal_data and can_update_personal:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        
        if data.financial_data and can_update_financial:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
        
        if data.real_estate_data and can_update_real_estate:
            await log_data_changes(process_id, user, process.get("real_estate_data"), data.real_estate_data.model_dump(), "dados imobiliários")
            update_data["real_estate_data"] = data.real_estate_data.model_dump()
        
        if data.credit_data and can_update_credit:
            await log_data_changes(process_id, user, process.get("credit_data"), data.credit_data.model_dump(), "dados de crédito")
            update_data["credit_data"] = data.credit_data.model_dump()
        
        if data.status and can_update_status and (data.status in valid_statuses or not valid_statuses):
            await log_history(process_id, user, "Alterou estado", "status", process["status"], data.status)
            update_data["status"] = data.status
            
            # Send email notification
            if process.get("client_email"):
                await send_email_notification(
                    process["client_email"],
                    f"Estado do Processo Atualizado",
                    f"O estado do seu processo foi atualizado para: {data.status}"
                )
    
    await db.processes.update_one({"id": process_id}, {"$set": update_data})
    updated = await db.processes.find_one({"id": process_id}, {"_id": 0})
    
    # Sincronizar com Trello (nome e descrição do card)
    await sync_process_to_trello(updated)
    
    return ProcessResponse(**updated)


@router.post("/{process_id}/assign")
async def assign_process(
    process_id: str, 
    consultor_id: Optional[str] = None,
    mediador_id: Optional[str] = None,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Assign consultor and/or mediador to a process"""
    process = await db.processes.find_one({"id": process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if consultor_id:
        # Check if user can act as consultor
        consultor = await db.users.find_one({"id": consultor_id})
        if not consultor or not UserRole.can_act_as_consultor(consultor.get("role", "")):
            raise HTTPException(status_code=404, detail="Consultor não encontrado ou inválido")
        update_data["assigned_consultor_id"] = consultor_id
        await log_history(process_id, user, "Atribuiu consultor", "assigned_consultor_id", None, consultor["name"])
    
    if mediador_id:
        # Check if user can act as mediador
        mediador = await db.users.find_one({"id": mediador_id})
        if not mediador or not UserRole.can_act_as_mediador(mediador.get("role", "")):
            raise HTTPException(status_code=404, detail="Mediador não encontrado ou inválido")
        update_data["assigned_mediador_id"] = mediador_id
        await log_history(process_id, user, "Atribuiu mediador", "assigned_mediador_id", None, mediador["name"])
    
    await db.processes.update_one({"id": process_id}, {"$set": update_data})
    return {"message": "Processo atribuído com sucesso"}
