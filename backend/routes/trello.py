"""
==============================================
TRELLO INTEGRATION ROUTES
==============================================
Endpoints para sincronização Trello ↔ CreditoIMO.
==============================================
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel

from database import db
from models.auth import UserRole
from services.auth import get_current_user, require_roles
from services.trello import (
    trello_service, TrelloService,
    trello_list_to_status, status_to_trello_list,
    build_card_description, parse_card_description,
    TRELLO_TO_STATUS
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trello", tags=["Trello Integration"])


class TrelloConfig(BaseModel):
    api_key: str
    token: str
    board_id: str


class SyncResult(BaseModel):
    success: bool
    created: int = 0
    updated: int = 0
    errors: List[str] = []
    message: str = ""


# === Configuração ===

@router.get("/status")
async def get_trello_status(user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))):
    """Verificar estado da integração Trello."""
    try:
        # Verificar se as credenciais estão configuradas
        if not trello_service.api_key or not trello_service.token:
            return {
                "connected": False,
                "message": "Credenciais Trello não configuradas",
                "board": None
            }
        
        # Testar conexão
        board = await trello_service.get_board()
        lists = await trello_service.get_lists()
        
        return {
            "connected": True,
            "message": "Conectado ao Trello",
            "board": {
                "id": board["id"],
                "name": board["name"],
                "url": board["url"],
                "lists_count": len(lists)
            },
            "lists": [{"id": l["id"], "name": l["name"]} for l in lists]
        }
    except Exception as e:
        logger.error(f"Erro ao verificar Trello: {e}")
        return {
            "connected": False,
            "message": f"Erro de conexão: {str(e)}",
            "board": None
        }


@router.post("/configure")
async def configure_trello(
    config: TrelloConfig,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Configurar credenciais do Trello."""
    # Guardar na base de dados
    await db.settings.update_one(
        {"key": "trello_config"},
        {"$set": {
            "key": "trello_config",
            "api_key": config.api_key,
            "token": config.token,
            "board_id": config.board_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user["id"]
        }},
        upsert=True
    )
    
    # Atualizar serviço
    trello_service.api_key = config.api_key
    trello_service.token = config.token
    trello_service.board_id = config.board_id
    
    # Testar conexão
    try:
        board = await trello_service.get_board()
        return {
            "success": True,
            "message": f"Conectado ao board: {board['name']}",
            "board_url": board["url"]
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Erro ao conectar: {str(e)}"
        }


# === Sincronização ===

@router.post("/reset-and-sync")
async def reset_and_sync_from_trello(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Apagar todos os dados existentes e importar tudo do Trello.
    ATENÇÃO: Esta operação é destrutiva e irreversível!
    """
    result = {
        "success": True,
        "deleted": {
            "processes": 0,
            "deadlines": 0,
            "tasks": 0,
            "activities": 0,
            "documents": 0,
            "emails": 0,
            "notifications": 0,
            "users": 0
        },
        "imported": {
            "processes": 0,
            "errors": []
        },
        "message": ""
    }
    
    try:
        # 1. Apagar dados existentes (exceto admins)
        logger.info("A apagar dados existentes...")
        
        # Apagar processos e dados relacionados
        del_processes = await db.processes.delete_many({})
        result["deleted"]["processes"] = del_processes.deleted_count
        
        del_deadlines = await db.deadlines.delete_many({})
        result["deleted"]["deadlines"] = del_deadlines.deleted_count
        
        del_tasks = await db.tasks.delete_many({})
        result["deleted"]["tasks"] = del_tasks.deleted_count
        
        del_activities = await db.activities.delete_many({})
        result["deleted"]["activities"] = del_activities.deleted_count
        
        del_documents = await db.documents.delete_many({})
        result["deleted"]["documents"] = del_documents.deleted_count
        
        del_emails = await db.emails.delete_many({})
        result["deleted"]["emails"] = del_emails.deleted_count
        
        del_notifications = await db.notifications.delete_many({})
        result["deleted"]["notifications"] = del_notifications.deleted_count
        
        # Apagar utilizadores não-admin
        del_users = await db.users.delete_many({"role": {"$ne": "admin"}})
        result["deleted"]["users"] = del_users.deleted_count
        
        logger.info(f"Dados apagados: {result['deleted']}")
        
        # 2. Importar cards do Trello
        logger.info("A importar do Trello...")
        lists = await trello_service.get_lists(force_refresh=True)
        all_cards = await trello_service.get_cards()
        
        logger.info(f"Encontrados {len(all_cards)} cards no Trello")
        
        for card in all_cards:
            try:
                # Encontrar a lista do card
                list_info = next((l for l in lists if l["id"] == card["idList"]), None)
                if not list_info:
                    result["imported"]["errors"].append(f"Lista não encontrada para card: {card.get('name', 'N/A')}")
                    continue
                
                # Converter para status do sistema
                status = trello_list_to_status(list_info["name"])
                if not status:
                    # Se a lista não estiver mapeada, usar um status genérico
                    status = "clientes_espera"
                    result["imported"]["errors"].append(f"Lista não mapeada '{list_info['name']}', usando 'clientes_espera'")
                
                # Extrair dados da descrição
                card_data = parse_card_description(card.get("desc", ""))
                
                # Criar novo processo
                new_process = {
                    "id": str(uuid.uuid4()),
                    "client_name": card["name"],
                    "client_email": card_data.get("email", ""),
                    "client_phone": card_data.get("telefone", card_data.get("phone", "")),
                    "client_nif": card_data.get("nif", ""),
                    "status": status,
                    "trello_card_id": card["id"],
                    "trello_list_id": card["idList"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "source": "trello_import",
                    "personal_data": {},
                    "financial_data": {},
                    "real_estate_data": {},
                    "credit_data": {},
                }
                
                await db.processes.insert_one(new_process)
                result["imported"]["processes"] += 1
                
            except Exception as e:
                result["imported"]["errors"].append(f"Erro no card {card.get('name', 'N/A')}: {str(e)}")
        
        result["message"] = f"Reset completo! Apagados {result['deleted']['processes']} processos. Importados {result['imported']['processes']} do Trello."
        logger.info(result["message"])
        
    except Exception as e:
        logger.error(f"Erro no reset e sync: {e}")
        result["success"] = False
        result["message"] = f"Erro: {str(e)}"
    
    return result


@router.post("/sync/from-trello", response_model=SyncResult)
async def sync_from_trello(
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Importar/sincronizar cards do Trello para o sistema."""
    result = SyncResult(success=True, message="")
    
    try:
        lists = await trello_service.get_lists()
        all_cards = await trello_service.get_cards()
        
        for card in all_cards:
            try:
                # Encontrar a lista do card
                list_info = next((l for l in lists if l["id"] == card["idList"]), None)
                if not list_info:
                    continue
                
                # Converter para status do sistema
                status = trello_list_to_status(list_info["name"])
                if not status:
                    result.errors.append(f"Lista não mapeada: {list_info['name']}")
                    continue
                
                # Verificar se já existe (pelo trello_card_id ou nome)
                existing = await db.processes.find_one({
                    "$or": [
                        {"trello_card_id": card["id"]},
                        {"client_name": card["name"]}
                    ]
                })
                
                if existing:
                    # Atualizar processo existente
                    update_data = {"status": status, "trello_card_id": card["id"]}
                    
                    # Só atualizar status se mudou
                    if existing.get("status") != status:
                        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                        await db.processes.update_one(
                            {"id": existing["id"]},
                            {"$set": update_data}
                        )
                        result.updated += 1
                else:
                    # Criar novo processo
                    card_data = parse_card_description(card.get("desc", ""))
                    
                    new_process = {
                        "id": str(uuid.uuid4()),
                        "client_name": card["name"],
                        "client_email": card_data.get("email", ""),
                        "client_phone": card_data.get("telefone", ""),
                        "status": status,
                        "trello_card_id": card["id"],
                        "trello_list_id": card["idList"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "source": "trello_import",
                        "personal_data": {},
                        "financial_data": {},
                        "real_estate_data": {},
                        "credit_data": {},
                    }
                    
                    await db.processes.insert_one(new_process)
                    result.created += 1
                    
            except Exception as e:
                result.errors.append(f"Erro no card {card.get('name', 'N/A')}: {str(e)}")
        
        result.message = f"Sincronização concluída: {result.created} criados, {result.updated} atualizados"
        
    except Exception as e:
        logger.error(f"Erro na sincronização: {e}")
        result.success = False
        result.message = f"Erro: {str(e)}"
    
    return result


@router.post("/sync/to-trello", response_model=SyncResult)
async def sync_to_trello(
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Exportar/sincronizar processos do sistema para o Trello."""
    result = SyncResult(success=True, message="")
    
    try:
        # Obter listas do Trello
        lists = await trello_service.get_lists()
        list_map = {l["name"].lower().strip(): l["id"] for l in lists}
        
        # Obter todos os processos
        processes = await db.processes.find({}, {"_id": 0}).to_list(1000)
        
        for process in processes:
            try:
                # Determinar lista de destino
                status = process.get("status", "clientes_espera")
                trello_list_name = status_to_trello_list(status)
                
                if not trello_list_name:
                    result.errors.append(f"Status não mapeado: {status}")
                    continue
                
                list_id = list_map.get(trello_list_name.lower())
                if not list_id:
                    result.errors.append(f"Lista não encontrada no Trello: {trello_list_name}")
                    continue
                
                # Construir descrição do card
                description = build_card_description(process)
                
                if process.get("trello_card_id"):
                    # Atualizar card existente
                    try:
                        await trello_service.update_card(
                            process["trello_card_id"],
                            name=process["client_name"],
                            desc=description,
                            idList=list_id
                        )
                        result.updated += 1
                    except Exception as e:
                        # Card pode ter sido eliminado no Trello
                        if "404" in str(e):
                            # Criar novo card
                            card = await trello_service.create_card(
                                list_id=list_id,
                                name=process["client_name"],
                                desc=description
                            )
                            await db.processes.update_one(
                                {"id": process["id"]},
                                {"$set": {"trello_card_id": card["id"], "trello_list_id": list_id}}
                            )
                            result.created += 1
                        else:
                            raise
                else:
                    # Criar novo card
                    card = await trello_service.create_card(
                        list_id=list_id,
                        name=process["client_name"],
                        desc=description
                    )
                    
                    # Guardar referência
                    await db.processes.update_one(
                        {"id": process["id"]},
                        {"$set": {"trello_card_id": card["id"], "trello_list_id": list_id}}
                    )
                    result.created += 1
                    
            except Exception as e:
                result.errors.append(f"Erro no processo {process.get('client_name', 'N/A')}: {str(e)}")
        
        result.message = f"Sincronização concluída: {result.created} criados, {result.updated} atualizados"
        
    except Exception as e:
        logger.error(f"Erro na sincronização: {e}")
        result.success = False
        result.message = f"Erro: {str(e)}"
    
    return result


@router.post("/sync/full", response_model=SyncResult)
async def full_sync(
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Sincronização completa bidirecional."""
    # Primeiro importar do Trello
    from_result = await sync_from_trello(BackgroundTasks(), user)
    
    # Depois exportar para o Trello
    to_result = await sync_to_trello(user)
    
    return SyncResult(
        success=from_result.success and to_result.success,
        created=from_result.created + to_result.created,
        updated=from_result.updated + to_result.updated,
        errors=from_result.errors + to_result.errors,
        message=f"Trello→Sistema: {from_result.created}+{from_result.updated} | Sistema→Trello: {to_result.created}+{to_result.updated}"
    )


# === Webhook para sincronização em tempo real ===

@router.post("/webhook")
async def trello_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint para receber webhooks do Trello.
    O Trello envia notificações quando há alterações no board.
    """
    try:
        body = await request.json()
        action = body.get("action", {})
        action_type = action.get("type", "")
        
        logger.info(f"Trello webhook: {action_type}")
        
        # Processar diferentes tipos de ações
        if action_type == "createCard":
            await handle_card_created(action)
        elif action_type == "updateCard":
            await handle_card_updated(action)
        elif action_type == "deleteCard":
            await handle_card_deleted(action)
        elif action_type == "moveCardToBoard":
            await handle_card_moved(action)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Erro no webhook Trello: {e}")
        return {"status": "error", "message": str(e)}


@router.head("/webhook")
async def trello_webhook_verify():
    """Verificação HEAD do webhook pelo Trello."""
    return {"status": "ok"}


async def handle_card_created(action: dict):
    """Processar criação de card no Trello."""
    card = action.get("data", {}).get("card", {})
    list_info = action.get("data", {}).get("list", {})
    
    if not card.get("id"):
        return
    
    # Verificar se já existe
    existing = await db.processes.find_one({"trello_card_id": card["id"]})
    if existing:
        return
    
    # Converter status
    status = trello_list_to_status(list_info.get("name", ""))
    if not status:
        status = "clientes_espera"
    
    # Criar processo
    new_process = {
        "id": str(uuid.uuid4()),
        "client_name": card.get("name", "Sem nome"),
        "status": status,
        "trello_card_id": card["id"],
        "trello_list_id": list_info.get("id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "trello_webhook",
        "personal_data": {},
        "financial_data": {},
        "real_estate_data": {},
        "credit_data": {},
    }
    
    await db.processes.insert_one(new_process)
    logger.info(f"Processo criado via Trello: {card.get('name')}")


async def handle_card_updated(action: dict):
    """Processar atualização de card no Trello."""
    card = action.get("data", {}).get("card", {})
    list_after = action.get("data", {}).get("listAfter", {})
    old_data = action.get("data", {}).get("old", {})
    
    if not card.get("id"):
        return
    
    # Encontrar processo
    process = await db.processes.find_one({"trello_card_id": card["id"]})
    if not process:
        # Se não existe, criar novo processo
        await handle_card_created(action)
        return
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    # Atualizar nome se mudou
    if card.get("name") and card["name"] != process.get("client_name"):
        update_data["client_name"] = card["name"]
        logger.info(f"Nome atualizado via Trello: {process.get('client_name')} -> {card['name']}")
    
    # Atualizar descrição se mudou (extrair dados)
    if "desc" in old_data or card.get("desc"):
        desc = card.get("desc", "")
        parsed = parse_card_description(desc)
        
        if parsed.get("email"):
            update_data["client_email"] = parsed["email"]
        if parsed.get("telefone") or parsed.get("phone"):
            update_data["client_phone"] = parsed.get("telefone") or parsed.get("phone")
        if parsed.get("nif"):
            update_data["client_nif"] = parsed["nif"]
    
    # Atualizar status se mudou de lista
    if list_after.get("name"):
        new_status = trello_list_to_status(list_after["name"])
        if new_status and new_status != process.get("status"):
            update_data["status"] = new_status
            update_data["trello_list_id"] = list_after.get("id")
            logger.info(f"Processo movido via Trello: {process['client_name']} -> {new_status}")
    
    if len(update_data) > 1:  # Mais do que apenas updated_at
        await db.processes.update_one({"id": process["id"]}, {"$set": update_data})
        logger.info(f"Processo atualizado via webhook Trello: {process['client_name']}")


async def handle_card_deleted(action: dict):
    """Processar eliminação de card no Trello."""
    card = action.get("data", {}).get("card", {})
    
    if not card.get("id"):
        return
    
    # Encontrar e marcar como eliminado (não eliminamos dados)
    await db.processes.update_one(
        {"trello_card_id": card["id"]},
        {"$set": {
            "trello_deleted": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    logger.info(f"Card eliminado no Trello: {card.get('id')}")


async def handle_card_moved(action: dict):
    """Processar movimentação de card entre listas."""
    await handle_card_updated(action)


# === Gestão de Webhooks ===

@router.post("/webhook/setup")
async def setup_webhook(
    callback_url: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Configurar webhook para sincronização em tempo real."""
    try:
        webhook = await trello_service.create_webhook(
            callback_url=callback_url,
            description="CreditoIMO Real-time Sync"
        )
        
        # Guardar referência
        await db.settings.update_one(
            {"key": "trello_webhook"},
            {"$set": {
                "key": "trello_webhook",
                "webhook_id": webhook["id"],
                "callback_url": callback_url,
                "created_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        
        return {
            "success": True,
            "webhook_id": webhook["id"],
            "message": "Webhook configurado com sucesso"
        }
    except Exception as e:
        logger.error(f"Erro ao criar webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/list")
async def list_webhooks(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Listar webhooks ativos."""
    try:
        webhooks = await trello_service.get_webhooks()
        return {"webhooks": webhooks}
    except Exception as e:
        return {"webhooks": [], "error": str(e)}


@router.delete("/webhook/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Eliminar webhook."""
    try:
        await trello_service.delete_webhook(webhook_id)
        await db.settings.delete_one({"key": "trello_webhook", "webhook_id": webhook_id})
        return {"success": True, "message": "Webhook eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
