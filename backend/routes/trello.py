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


# === Função auxiliar para atribuição automática ===

async def find_matching_user(trello_members: list) -> dict:
    """
    Encontrar utilizador da aplicação correspondente aos membros do Trello.
    
    Procura por (ordem de prioridade):
    1. Username do Trello corresponde à parte local do email (ex: pedroborges249 ~ pedroborges@...)
    2. Email exacto
    3. Nome exacto (case-insensitive)
    
    Retorna dict com assigned_consultor_id e/ou assigned_mediador_id
    """
    result = {
        "assigned_consultor_id": None,
        "assigned_mediador_id": None,
        "consultor_name": None,
        "mediador_name": None,
        "matched_members": []
    }
    
    if not trello_members:
        return result
    
    # Obter todos os utilizadores ativos da aplicação
    users = await db.users.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(500)
    
    # Criar mapas para busca rápida
    users_by_email = {u.get("email", "").lower().strip(): u for u in users if u.get("email")}
    users_by_name = {u["name"].lower().strip(): u for u in users}
    # Mapa por parte local do email (antes do @)
    users_by_email_local = {}
    for u in users:
        if u.get("email") and "@" in u["email"]:
            local_part = u["email"].split("@")[0].lower().strip()
            users_by_email_local[local_part] = u
    
    for member in trello_members:
        member_name = member.get("fullName", "").lower().strip()
        member_username = member.get("username", "").lower().strip()
        member_email = member.get("email", "").lower().strip()
        
        matched_user = None
        match_method = None
        
        # 1. PRIORIDADE: Username do Trello começa com parte local do email
        # Ex: pedroborges249 começa com "pedroborges" (de pedroborges@powerealestate.pt)
        if member_username:
            for local_part, user in users_by_email_local.items():
                # Verificar se username começa com a parte local do email
                # ou se a parte local começa com o username (sem números)
                username_clean = ''.join(c for c in member_username if not c.isdigit())
                if member_username.startswith(local_part) or local_part.startswith(username_clean):
                    matched_user = user
                    match_method = "email_local"
                    break
        
        # 2. Email exacto do Trello
        if not matched_user and member_email and member_email in users_by_email:
            matched_user = users_by_email[member_email]
            match_method = "email_exact"
        
        # 3. Username como email direto
        if not matched_user and member_username and member_username in users_by_email:
            matched_user = users_by_email[member_username]
            match_method = "username_as_email"
        
        # 4. Fallback: Tentar encontrar por nome
        if not matched_user and member_name and member_name in users_by_name:
            matched_user = users_by_name[member_name]
            match_method = "name"
        
        if matched_user:
            result["matched_members"].append({
                "trello_member": member.get("fullName"),
                "trello_email": member_email or member_username,
                "matched_user": matched_user["name"],
                "matched_email": matched_user.get("email"),
                "role": matched_user["role"],
                "match_method": match_method
            })
            
            # Atribuir baseado no papel do utilizador
            role = matched_user["role"]
            
            # Papéis que podem ser consultores
            if role in ["consultor", "diretor", "admin", "ceo"]:
                if not result["assigned_consultor_id"]:
                    result["assigned_consultor_id"] = matched_user["id"]
                    result["consultor_name"] = matched_user["name"]
            
            # Papéis que podem ser intermediários
            if role in ["mediador", "intermediario", "intermediario_credito", "diretor"]:
                if not result["assigned_mediador_id"]:
                    result["assigned_mediador_id"] = matched_user["id"]
                    result["mediador_name"] = matched_user["name"]
    
    return result


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
    """Verificar estado da integração Trello com diagnósticos detalhados."""
    # Informação de configuração (mesmo que falhe a conexão)
    config_info = {
        "has_api_key": bool(trello_service.api_key),
        "has_token": bool(trello_service.token),
        "has_board_id": bool(trello_service.board_id),
        "board_id": trello_service.board_id[:8] + "..." if trello_service.board_id and len(trello_service.board_id) > 8 else trello_service.board_id
    }
    
    try:
        # Verificar se as credenciais estão configuradas
        if not trello_service.api_key or not trello_service.token:
            return {
                "connected": False,
                "message": "Credenciais Trello não configuradas",
                "board": None,
                "config": config_info,
                "error": "TRELLO_API_KEY e/ou TRELLO_TOKEN não definidos nas variáveis de ambiente"
            }
        
        if not trello_service.board_id:
            return {
                "connected": False,
                "message": "Board ID não configurado",
                "board": None,
                "config": config_info,
                "error": "TRELLO_BOARD_ID não definido nas variáveis de ambiente"
            }
        
        # Testar conexão
        board = await trello_service.get_board()
        lists = await trello_service.get_lists()
        
        # Obter estatísticas da sincronização
        last_sync = await db.settings.find_one({"key": "trello_last_sync"}, {"_id": 0})
        
        # Contar processos sincronizados
        total_processes = await db.processes.count_documents({})
        trello_processes = await db.processes.count_documents({"trello_card_id": {"$exists": True, "$ne": None}})
        assigned_processes = await db.processes.count_documents({
            "$or": [
                {"assigned_consultor_id": {"$exists": True, "$ne": None}},
                {"assigned_mediador_id": {"$exists": True, "$ne": None}}
            ]
        })
        
        # Obter membros do board para diagnóstico
        board_members = []
        try:
            members_response = await trello_service._request("GET", f"/boards/{trello_service.board_id}/members")
            board_members = [{"id": m.get("id"), "name": m.get("fullName"), "username": m.get("username")} for m in members_response]
        except Exception as e:
            logger.warning(f"Não foi possível obter membros do board: {e}")
        
        # Verificar correspondência de membros com utilizadores da app
        app_users = await db.users.find(
            {"is_active": {"$ne": False}},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
        ).to_list(100)
        
        # Criar mapas para busca
        users_by_email = {u.get("email", "").lower().strip(): u for u in app_users if u.get("email")}
        users_by_name = {u["name"].lower().strip(): u for u in app_users}
        users_by_email_local = {}
        for u in app_users:
            if u.get("email") and "@" in u["email"]:
                local_part = u["email"].split("@")[0].lower().strip()
                users_by_email_local[local_part] = u
        
        member_mapping = []
        for member in board_members:
            member_username = member.get("username", "").lower().strip()
            member_name = member.get("name", "").lower().strip()
            
            matched = None
            match_method = None
            
            # 1. PRIORIDADE: Username começa com parte local do email
            if member_username:
                for local_part, user in users_by_email_local.items():
                    username_clean = ''.join(c for c in member_username if not c.isdigit())
                    if member_username.startswith(local_part) or local_part.startswith(username_clean):
                        matched = user
                        match_method = "email"
                        break
            
            # 2. Nome exacto
            if not matched and member_name in users_by_name:
                matched = users_by_name[member_name]
                match_method = "name"
            
            member_mapping.append({
                "trello_name": member.get("name"),
                "trello_username": member.get("username"),
                "app_user": matched["name"] if matched else None,
                "app_email": matched.get("email") if matched else None,
                "app_role": matched["role"] if matched else None,
                "matched": matched is not None,
                "match_method": match_method
            })
        
        return {
            "connected": True,
            "message": "Conectado ao Trello",
            "board": {
                "id": board["id"],
                "name": board["name"],
                "url": board["url"],
                "lists_count": len(lists)
            },
            "lists": [{"id": l["id"], "name": l["name"]} for l in lists],
            "config": config_info,
            "sync_stats": {
                "total_processes": total_processes,
                "trello_synced": trello_processes,
                "with_assignment": assigned_processes,
                "without_assignment": trello_processes - assigned_processes,
                "last_sync": last_sync.get("timestamp") if last_sync else None
            },
            "member_mapping": member_mapping,
            "board_members_count": len(board_members),
            "app_users_count": len(app_users)
        }
    except Exception as e:
        logger.error(f"Erro ao verificar Trello: {e}")
        return {
            "connected": False,
            "message": f"Erro de conexão: {str(e)}",
            "board": None,
            "config": config_info,
            "error": str(e)
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
            "assignments": 0,
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
        
        # 2. Importar cards do Trello com todos os detalhes
        logger.info("A importar do Trello...")
        lists = await trello_service.get_lists(force_refresh=True)
        all_cards = await trello_service.get_cards_with_details()
        
        logger.info(f"Encontrados {len(all_cards)} cards no Trello")
        
        result["imported"]["activities"] = 0
        
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
                    status = "clientes_espera"
                    result["imported"]["errors"].append(f"Lista não mapeada '{list_info['name']}', usando 'clientes_espera'")
                
                # Extrair dados da descrição
                card_data = parse_card_description(card.get("desc", ""))
                
                # Gerar ID e número do processo
                process_id = str(uuid.uuid4())
                process_number = result["imported"]["processes"] + 1
                
                # Extrair labels do Trello
                trello_labels = [l.get("name") for l in card.get("labels", []) if l.get("name")]
                
                # Verificar flags especiais baseadas em labels
                idade_menos_35 = any("35" in l.lower() or "menos" in l.lower() for l in trello_labels)
                prioridade = any("prioridade" in l.lower() for l in trello_labels)
                docs_preparados = any("documento" in l.lower() and "preparad" in l.lower() for l in trello_labels)
                ch_aprovado = any("aprovado" in l.lower() for l in trello_labels)
                
                # Extrair MEMBROS atribuídos ao cartão (utilizadores do Trello)
                trello_members = card.get("members", [])
                assigned_members = [m.get("fullName") for m in trello_members if m.get("fullName")]
                assigned_member_ids = card.get("idMembers", [])
                
                # ATRIBUIÇÃO AUTOMÁTICA: Encontrar utilizadores correspondentes
                assignment = await find_matching_user(trello_members)
                
                # Criar novo processo com todos os dados do Trello
                new_process = {
                    "id": process_id,
                    "process_number": process_number,
                    "client_name": card["name"],
                    "client_email": card_data.get("email", card_data.get("📧_email", "")),
                    "client_phone": card_data.get("telefone", card_data.get("phone", card_data.get("📱_telefone", ""))),
                    "client_nif": card_data.get("nif", card_data.get("🆔_nif", "")),
                    "status": status,
                    "trello_card_id": card["id"],
                    "trello_list_id": card["idList"],
                    "trello_url": card.get("shortUrl", ""),
                    "created_at": card.get("dateLastActivity", datetime.now(timezone.utc).isoformat()),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "source": "trello_import",
                    "notes": card.get("desc", ""),
                    # Labels e flags do Trello
                    "labels": trello_labels,
                    "idade_menos_35": idade_menos_35,
                    "prioridade": prioridade,
                    "docs_preparados": docs_preparados,
                    "ch_aprovado": ch_aprovado,
                    # Due date do Trello
                    "due_date": card.get("due"),
                    "due_complete": card.get("dueComplete", False),
                    # Membros atribuídos do Trello
                    "trello_members": assigned_members,  # Nomes dos membros
                    "trello_member_ids": assigned_member_ids,  # IDs dos membros
                    # ATRIBUIÇÃO AUTOMÁTICA
                    "assigned_consultor_id": assignment["assigned_consultor_id"],
                    "assigned_mediador_id": assignment["assigned_mediador_id"],
                    "consultor_name": assignment["consultor_name"],
                    "mediador_name": assignment["mediador_name"],
                    # Dados estruturados
                    "personal_data": {
                        "morada_fiscal": card_data.get("morada", card_data.get("📍_morada", "")),
                        "data_nascimento": card_data.get("nascimento", card_data.get("🎂_nascimento", "")),
                    },
                    "financial_data": {
                        "rendimento_mensal": card_data.get("rendimento", ""),
                        "valor_pretendido": card_data.get("valor_pretendido", card_data.get("🏦_valor_pretendido", "")),
                    },
                    "real_estate_data": {
                        "morada_imovel": card_data.get("imovel", card_data.get("🏠_imóvel", "")),
                        "valor_aquisicao": card_data.get("valor_aquisicao", card_data.get("💶_valor_aquisição", "")),
                    },
                    "credit_data": {},
                }
                
                await db.processes.insert_one(new_process)
                result["imported"]["processes"] += 1
                
                # Contar atribuições
                if assignment["assigned_consultor_id"] or assignment["assigned_mediador_id"]:
                    result["imported"]["assignments"] += 1
                
                # Importar comentários/atividades do Trello como atividades do sistema
                comments = card.get("comments", [])
                for comment in comments:
                    try:
                        activity = {
                            "id": str(uuid.uuid4()),
                            "process_id": process_id,
                            "type": "comment",
                            "title": "Comentário do Trello",
                            "description": comment.get("data", {}).get("text", ""),
                            "created_at": comment.get("date", datetime.now(timezone.utc).isoformat()),
                            "created_by": comment.get("memberCreator", {}).get("fullName", "Trello"),
                            "source": "trello_import",
                            "trello_action_id": comment.get("id")
                        }
                        await db.activities.insert_one(activity)
                        result["imported"]["activities"] += 1
                    except Exception as e:
                        logger.warning(f"Erro ao importar comentário: {e}")
                
            except Exception as e:
                result["imported"]["errors"].append(f"Erro no card {card.get('name', 'N/A')}: {str(e)}")
        
        result["message"] = f"Reset completo! Apagados {result['deleted']['processes']} processos. Importados {result['imported']['processes']} do Trello com {result['imported']['activities']} atividades e {result['imported']['assignments']} atribuições automáticas."
        logger.info(result["message"])
        
        # Guardar timestamp da última sincronização
        await db.settings.update_one(
            {"key": "trello_last_sync"},
            {"$set": {
                "key": "trello_last_sync",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "by": user["name"],
                "type": "reset_and_sync"
            }},
            upsert=True
        )
        
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
    """Importar/sincronizar cards do Trello para o sistema com atribuição automática."""
    result = SyncResult(success=True, message="")
    assignments_made = 0
    
    try:
        lists = await trello_service.get_lists()
        # Usar get_cards_with_details para obter membros
        all_cards = await trello_service.get_cards_with_details()
        
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
                
                # Obter membros do card para atribuição automática
                trello_members = card.get("members", [])
                assignment = await find_matching_user(trello_members)
                
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
                    
                    # Atribuir utilizadores se não estiverem já atribuídos
                    if assignment["assigned_consultor_id"] and not existing.get("assigned_consultor_id"):
                        update_data["assigned_consultor_id"] = assignment["assigned_consultor_id"]
                        update_data["consultor_name"] = assignment["consultor_name"]
                        assignments_made += 1
                    
                    if assignment["assigned_mediador_id"] and not existing.get("assigned_mediador_id"):
                        update_data["assigned_mediador_id"] = assignment["assigned_mediador_id"]
                        update_data["mediador_name"] = assignment["mediador_name"]
                        assignments_made += 1
                    
                    # Guardar membros do Trello para referência
                    if trello_members:
                        update_data["trello_members"] = [m.get("fullName") for m in trello_members if m.get("fullName")]
                    
                    # Só atualizar se há mudanças
                    if existing.get("status") != status or len(update_data) > 2:
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
                        # Atribuição automática
                        "assigned_consultor_id": assignment["assigned_consultor_id"],
                        "assigned_mediador_id": assignment["assigned_mediador_id"],
                        "consultor_name": assignment["consultor_name"],
                        "mediador_name": assignment["mediador_name"],
                        # Guardar membros do Trello para referência
                        "trello_members": [m.get("fullName") for m in trello_members if m.get("fullName")],
                    }
                    
                    if assignment["assigned_consultor_id"] or assignment["assigned_mediador_id"]:
                        assignments_made += 1
                    
                    await db.processes.insert_one(new_process)
                    result.created += 1
                    
            except Exception as e:
                result.errors.append(f"Erro no card {card.get('name', 'N/A')}: {str(e)}")
        
        # Guardar timestamp da última sincronização
        await db.settings.update_one(
            {"key": "trello_last_sync"},
            {"$set": {
                "key": "trello_last_sync",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "by": user["name"]
            }},
            upsert=True
        )
        
        result.message = f"Sincronização concluída: {result.created} criados, {result.updated} atualizados, {assignments_made} atribuições automáticas"
        
    except Exception as e:
        logger.error(f"Erro na sincronização: {e}")
        result.success = False
        result.message = f"Erro: {str(e)}"
    
    return result


@router.post("/assign-existing", response_model=SyncResult)
async def assign_existing_processes(
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """
    Atribuir automaticamente processos existentes a utilizadores.
    
    Este endpoint percorre todos os processos que têm membros do Trello
    mas não têm consultor/mediador atribuído, e tenta fazer a correspondência.
    Útil para corrigir processos já importados.
    """
    result = SyncResult(success=True, message="")
    
    try:
        # Buscar processos sem atribuição mas com membros do Trello
        processes = await db.processes.find(
            {
                "$and": [
                    {"trello_card_id": {"$exists": True, "$ne": None}},
                    {"$or": [
                        {"assigned_consultor_id": {"$exists": False}},
                        {"assigned_consultor_id": None},
                        {"assigned_mediador_id": {"$exists": False}},
                        {"assigned_mediador_id": None}
                    ]}
                ]
            },
            {"_id": 0}
        ).to_list(1000)
        
        logger.info(f"Encontrados {len(processes)} processos para verificar atribuição")
        
        # Obter cards do Trello para obter membros atualizados
        all_cards = await trello_service.get_cards_with_details()
        cards_by_id = {c["id"]: c for c in all_cards}
        
        for process in processes:
            try:
                card_id = process.get("trello_card_id")
                card = cards_by_id.get(card_id)
                
                if not card:
                    # Tentar usar membros guardados no processo
                    trello_members = []
                    if process.get("trello_members"):
                        trello_members = [{"fullName": name} for name in process["trello_members"]]
                else:
                    trello_members = card.get("members", [])
                
                if not trello_members:
                    continue
                
                # Encontrar correspondência
                assignment = await find_matching_user(trello_members)
                
                update_data = {}
                
                # Só atribuir se não tiver já atribuição
                if assignment["assigned_consultor_id"] and not process.get("assigned_consultor_id"):
                    update_data["assigned_consultor_id"] = assignment["assigned_consultor_id"]
                    update_data["consultor_name"] = assignment["consultor_name"]
                
                if assignment["assigned_mediador_id"] and not process.get("assigned_mediador_id"):
                    update_data["assigned_mediador_id"] = assignment["assigned_mediador_id"]
                    update_data["mediador_name"] = assignment["mediador_name"]
                
                if update_data:
                    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                    await db.processes.update_one(
                        {"id": process["id"]},
                        {"$set": update_data}
                    )
                    result.updated += 1
                    logger.info(f"Processo '{process.get('client_name')}' atribuído: {update_data}")
                
            except Exception as e:
                result.errors.append(f"Erro no processo {process.get('client_name', 'N/A')}: {str(e)}")
        
        result.message = f"Atribuição concluída: {result.updated} processos atualizados"
        
    except Exception as e:
        logger.error(f"Erro na atribuição: {e}")
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
    callback_url: Optional[str] = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Configurar webhook para sincronização em tempo real."""
    try:
        # Se não for fornecido, usar o URL do ambiente
        if not callback_url:
            import os
            base_url = os.environ.get("WEBHOOK_BASE_URL")
            if not base_url:
                raise HTTPException(
                    status_code=400, 
                    detail="WEBHOOK_BASE_URL não configurado. Configure a variável de ambiente ou forneça callback_url."
                )
            callback_url = f"{base_url}/api/trello/webhook"
        
        # Verificar se já existe webhook ativo
        existing_webhooks = await trello_service.get_webhooks()
        for wh in existing_webhooks:
            if wh.get("callbackURL") == callback_url:
                return {
                    "success": True,
                    "webhook_id": wh["id"],
                    "message": "Webhook já está configurado",
                    "callback_url": callback_url
                }
        
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
            "message": "Webhook configurado com sucesso",
            "callback_url": callback_url
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
