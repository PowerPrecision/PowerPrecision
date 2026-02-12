"""
====================================================================
ÍNDICES DE BASE DE DADOS - OPTIMIZAÇÃO DE PERFORMANCE
====================================================================
Script para criar índices nas colecções MongoDB mais consultadas.
Melhora significativamente o tempo de resposta para queries frequentes.

Executar manualmente ou na inicialização da aplicação.
====================================================================
"""
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


# Lista de índices antigos/incorretos que devem ser removidos
DEPRECATED_INDEXES = {
    "properties": [
        "idx_internal_ref",  # Nome antigo incorreto - campo era internal_ref
    ]
}


async def cleanup_deprecated_indexes(db) -> dict:
    """
    Remove índices antigos/incorretos que podem causar erros.
    Executa antes de criar novos índices.
    """
    results = {"dropped": [], "errors": [], "not_found": []}
    
    for collection_name, index_names in DEPRECATED_INDEXES.items():
        collection = getattr(db, collection_name)
        
        try:
            # Obter índices existentes
            existing_indexes = await collection.index_information()
            
            for idx_name in index_names:
                if idx_name in existing_indexes:
                    try:
                        await collection.drop_index(idx_name)
                        results["dropped"].append(f"{collection_name}.{idx_name}")
                        logger.info(f"🗑️ Índice removido: {collection_name}.{idx_name}")
                    except Exception as e:
                        results["errors"].append(f"{collection_name}.{idx_name}: {str(e)}")
                        logger.error(f"Erro ao remover índice {collection_name}.{idx_name}: {e}")
                else:
                    results["not_found"].append(f"{collection_name}.{idx_name}")
        except Exception as e:
            results["errors"].append(f"{collection_name}: {str(e)}")
            logger.error(f"Erro ao verificar índices em {collection_name}: {e}")
    
    if results["dropped"]:
        logger.info(f"✅ Limpeza de índices concluída: {len(results['dropped'])} removidos")
    
    return results


async def create_indexes(db) -> dict:
    """
    Cria índices optimizados nas colecções principais.
    
    Returns:
        dict: Resumo dos índices criados
    """
    # Primeiro, limpar índices antigos/incorretos
    cleanup_results = await cleanup_deprecated_indexes(db)
    
    results = {
        "created": [],
        "errors": [],
        "skipped": [],
        "cleanup": cleanup_results
    }
    
    # ====================================================================
    # ÍNDICES PARA COLECÇÃO 'processes'
    # ====================================================================
    process_indexes = [
        # Índice no status - muito usado em filtros e dashboard
        {"keys": [("status", 1)], "name": "idx_status"},
        
        # Índice no nome do cliente - usado em pesquisa
        {"keys": [("client_name", 1)], "name": "idx_client_name"},
        
        # Índice no email do cliente - usado em lookup
        {"keys": [("client_email", 1)], "name": "idx_client_email"},
        
        # Índice na data de criação - usado para ordenação
        {"keys": [("created_at", -1)], "name": "idx_created_at_desc"},
        
        # Índice no consultor atribuído - usado em filtros por utilizador
        {"keys": [("assigned_consultor_id", 1)], "name": "idx_consultor"},
        
        # Índice no mediador atribuído
        {"keys": [("assigned_mediador_id", 1)], "name": "idx_mediador"},
        
        # Índice composto status + created_at - muito usado em listagens
        {"keys": [("status", 1), ("created_at", -1)], "name": "idx_status_created"},
        
        # Índice no NIF para pesquisa rápida
        {"keys": [("personal_data.nif", 1)], "name": "idx_nif", "sparse": True},
        
        # Índice no tipo de processo
        {"keys": [("process_type", 1)], "name": "idx_process_type"},
        
        # Índice de texto para pesquisa full-text
        {
            "keys": [
                ("client_name", "text"), 
                ("client_email", "text"),
                ("personal_data.nif", "text")
            ], 
            "name": "idx_text_search"
        },
    ]
    
    for idx in process_indexes:
        try:
            await db.processes.create_index(
                idx["keys"],
                name=idx["name"],
                sparse=idx.get("sparse", False),
                background=True  # Não bloqueia operações durante criação
            )
            results["created"].append(f"processes.{idx['name']}")
            logger.info(f"Índice criado: processes.{idx['name']}")
        except Exception as e:
            if "already exists" in str(e).lower():
                results["skipped"].append(f"processes.{idx['name']}")
            else:
                results["errors"].append(f"processes.{idx['name']}: {str(e)}")
                logger.error(f"Erro ao criar índice processes.{idx['name']}: {e}")
    
    # ====================================================================
    # ÍNDICES PARA COLECÇÃO 'users'
    # ====================================================================
    user_indexes = [
        # Índice único no email - login
        {"keys": [("email", 1)], "name": "idx_email", "unique": True},
        
        # Índice no ID do utilizador
        {"keys": [("id", 1)], "name": "idx_user_id", "unique": True},
        
        # Índice no role - filtros por tipo de utilizador
        {"keys": [("role", 1)], "name": "idx_role"},
        
        # Índice composto role + is_active
        {"keys": [("role", 1), ("is_active", 1)], "name": "idx_role_active"},
    ]
    
    for idx in user_indexes:
        try:
            await db.users.create_index(
                idx["keys"],
                name=idx["name"],
                unique=idx.get("unique", False),
                sparse=idx.get("sparse", False),
                background=True
            )
            results["created"].append(f"users.{idx['name']}")
            logger.info(f"Índice criado: users.{idx['name']}")
        except Exception as e:
            if "already exists" in str(e).lower():
                results["skipped"].append(f"users.{idx['name']}")
            else:
                results["errors"].append(f"users.{idx['name']}: {str(e)}")
                logger.error(f"Erro ao criar índice users.{idx['name']}: {e}")
    
    # ====================================================================
    # ÍNDICES PARA COLECÇÃO 'system_error_logs'
    # ====================================================================
    log_indexes = [
        # Índice no timestamp - queries por período
        {"keys": [("timestamp", -1)], "name": "idx_timestamp_desc"},
        
        # Índice na severidade - filtros
        {"keys": [("severity", 1)], "name": "idx_severity"},
        
        # Índice no componente - filtros
        {"keys": [("component", 1)], "name": "idx_component"},
        
        # Índice composto para queries frequentes
        {"keys": [("timestamp", -1), ("severity", 1)], "name": "idx_time_severity"},
        
        # TTL index - auto-delete logs após 90 dias
        {"keys": [("timestamp", 1)], "name": "idx_ttl", "expireAfterSeconds": 7776000},
    ]
    
    for idx in log_indexes:
        try:
            create_options = {
                "name": idx["name"],
                "background": True
            }
            if "expireAfterSeconds" in idx:
                create_options["expireAfterSeconds"] = idx["expireAfterSeconds"]
            
            await db.system_error_logs.create_index(idx["keys"], **create_options)
            results["created"].append(f"system_error_logs.{idx['name']}")
            logger.info(f"Índice criado: system_error_logs.{idx['name']}")
        except Exception as e:
            if "already exists" in str(e).lower():
                results["skipped"].append(f"system_error_logs.{idx['name']}")
            else:
                results["errors"].append(f"system_error_logs.{idx['name']}: {str(e)}")
                logger.error(f"Erro ao criar índice system_error_logs.{idx['name']}: {e}")
    
    # ====================================================================
    # ÍNDICES PARA COLECÇÃO 'properties' (Imóveis)
    # ====================================================================
    property_indexes = [
        {"keys": [("internal_reference", 1)], "name": "idx_internal_reference", "unique": True, "sparse": True},
        {"keys": [("status", 1)], "name": "idx_property_status"},
        {"keys": [("address.district", 1), ("address.municipality", 1)], "name": "idx_location"},
        {"keys": [("financials.asking_price", 1)], "name": "idx_asking_price"},
        {"keys": [("created_at", -1)], "name": "idx_created_desc"},
    ]
    
    for idx in property_indexes:
        try:
            await db.properties.create_index(
                idx["keys"],
                name=idx["name"],
                unique=idx.get("unique", False),
                sparse=idx.get("sparse", False),
                background=True
            )
            results["created"].append(f"properties.{idx['name']}")
            logger.info(f"Índice criado: properties.{idx['name']}")
        except Exception as e:
            if "already exists" in str(e).lower():
                results["skipped"].append(f"properties.{idx['name']}")
            else:
                results["errors"].append(f"properties.{idx['name']}: {str(e)}")
                logger.error(f"Erro ao criar índice properties.{idx['name']}: {e}")
    
    # ====================================================================
    # ÍNDICES PARA COLECÇÃO 'tasks'
    # ====================================================================
    task_indexes = [
        {"keys": [("process_id", 1)], "name": "idx_process_id"},
        {"keys": [("assigned_to", 1)], "name": "idx_assigned_to"},
        {"keys": [("status", 1)], "name": "idx_task_status"},
        {"keys": [("due_date", 1)], "name": "idx_due_date"},
        {"keys": [("status", 1), ("due_date", 1)], "name": "idx_status_due"},
    ]
    
    for idx in task_indexes:
        try:
            await db.tasks.create_index(
                idx["keys"],
                name=idx["name"],
                background=True
            )
            results["created"].append(f"tasks.{idx['name']}")
            logger.info(f"Índice criado: tasks.{idx['name']}")
        except Exception as e:
            if "already exists" in str(e).lower():
                results["skipped"].append(f"tasks.{idx['name']}")
            else:
                results["errors"].append(f"tasks.{idx['name']}: {str(e)}")
                logger.error(f"Erro ao criar índice tasks.{idx['name']}: {e}")
    
    # Resumo
    logger.info(
        f"Criação de índices concluída: "
        f"{len(results['created'])} criados, "
        f"{len(results['skipped'])} já existiam, "
        f"{len(results['errors'])} erros"
    )
    
    return results


async def get_index_stats(db) -> dict:
    """
    Obtém estatísticas dos índices existentes.
    """
    stats = {}
    
    collections = ["processes", "users", "system_error_logs", "properties", "tasks"]
    
    for collection_name in collections:
        try:
            collection = getattr(db, collection_name)
            indexes = await collection.index_information()
            stats[collection_name] = {
                "count": len(indexes),
                "indexes": list(indexes.keys())
            }
        except Exception as e:
            stats[collection_name] = {"error": str(e)}
    
    return stats
