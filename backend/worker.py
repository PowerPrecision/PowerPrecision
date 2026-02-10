"""
====================================================================
ARQ WORKER - CREDITOIMO TASK QUEUE
====================================================================
Worker para processamento de tarefas em background.

TAREFAS DISPONÍVEIS:
- send_email_task: Envio de emails (notificações, confirmações)
- process_ai_document_task: Análise de documentos com IA
- sync_trello_task: Sincronização com Trello
- cleanup_temp_files_task: Limpeza de ficheiros temporários
- generate_report_task: Geração de relatórios

COMO EXECUTAR O WORKER:
    cd backend && arq worker.WorkerSettings

COMO EXECUTAR COM LOGS:
    cd backend && arq worker.WorkerSettings --verbose

MONITORIZAÇÃO:
    Logs são enviados para stdout e podem ser agregados com ferramentas como:
    - Papertrail, Datadog, ELK Stack, etc.

====================================================================
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from arq import cron
from arq.connections import RedisSettings, ArqRedis

# Importar configurações
from config import (
    get_redis_settings,
    TASK_JOB_TIMEOUT,
    TASK_MAX_TRIES,
    TASK_MAX_JOBS
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("arq.worker")


# ====================================================================
# CONTEXTO DO WORKER
# ====================================================================
async def startup(ctx: Dict[str, Any]) -> None:
    """
    Executado uma vez quando o worker inicia.
    Usado para inicializar conexões e recursos.
    """
    logger.info("🚀 Worker iniciando...")
    
    # Inicializar conexão à base de dados
    from database import db
    ctx["db"] = db
    
    # Inicializar serviço de email
    from services.email_v2 import email_service
    ctx["email_service"] = email_service
    
    logger.info("✅ Worker pronto para processar tarefas")


async def shutdown(ctx: Dict[str, Any]) -> None:
    """
    Executado quando o worker encerra.
    Usado para limpar recursos.
    """
    logger.info("🛑 Worker encerrando...")
    # Cleanup aqui se necessário
    logger.info("👋 Worker encerrado com sucesso")


# ====================================================================
# TAREFAS DE EMAIL
# ====================================================================
async def send_email_task(
    ctx: Dict[str, Any],
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    template: Optional[str] = None,
    template_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Tarefa para envio de emails.
    
    Args:
        ctx: Contexto do worker (contém db, email_service, etc.)
        to_email: Email do destinatário
        subject: Assunto
        body: Corpo em texto
        html_body: Corpo em HTML (opcional)
        template: Nome do template a usar (opcional)
        template_data: Dados para o template (opcional)
    
    Returns:
        Dict com resultado do envio
    """
    logger.info(f"📧 Enviando email para {to_email}: {subject}")
    
    try:
        email_service = ctx.get("email_service")
        
        if not email_service:
            from services.email_v2 import email_service as es
            email_service = es
        
        from services.email_v2 import EmailMessage
        
        message = EmailMessage(
            to=to_email,
            subject=subject,
            text_body=body,
            html_body=html_body
        )
        
        result = await email_service.send(message)
        
        if result.success:
            logger.info(f"✅ Email enviado com sucesso para {to_email}")
        else:
            logger.warning(f"⚠️ Falha ao enviar email: {result.error}")
        
        return {
            "success": result.success,
            "to": to_email,
            "subject": subject,
            "provider": result.provider,
            "message_id": result.message_id,
            "error": result.error
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar email para {to_email}: {str(e)}")
        raise  # Re-raise para ARQ fazer retry


async def send_registration_email_task(
    ctx: Dict[str, Any],
    client_email: str,
    client_name: str
) -> Dict[str, Any]:
    """Tarefa específica para email de confirmação de registo."""
    logger.info(f"📧 Enviando email de registo para {client_email}")
    
    try:
        from services.email import send_registration_confirmation
        success = await send_registration_confirmation(client_email, client_name)
        
        return {
            "success": success,
            "type": "registration_confirmation",
            "to": client_email,
            "client_name": client_name
        }
    except Exception as e:
        logger.error(f"❌ Erro no email de registo: {str(e)}")
        raise


# ====================================================================
# TAREFAS DE IA/DOCUMENTOS
# ====================================================================
async def process_ai_document_task(
    ctx: Dict[str, Any],
    process_id: str,
    document_data: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """
    Tarefa para processamento de documento com IA.
    
    Esta é uma tarefa pesada que pode demorar minutos.
    Ideal para executar em background.
    """
    logger.info(f"🤖 Processando documento IA para processo {process_id}")
    
    try:
        db = ctx.get("db")
        
        # Actualizar status do documento
        await db.processes.update_one(
            {"id": process_id},
            {
                "$set": {
                    "ai_processing_status": "processing",
                    "ai_processing_started": datetime.now(timezone.utc)
                }
            }
        )
        
        # Processar documento (simulação - implementar lógica real)
        # from services.ai_document import analyze_document
        # result = await analyze_document(document_data)
        
        # Simular processamento
        await asyncio.sleep(2)
        result = {"extracted_data": document_data, "confidence": 0.95}
        
        # Actualizar resultado
        await db.processes.update_one(
            {"id": process_id},
            {
                "$set": {
                    "ai_processing_status": "completed",
                    "ai_processing_completed": datetime.now(timezone.utc),
                    "ai_extracted_data": result
                }
            }
        )
        
        logger.info(f"✅ Documento processado com sucesso: {process_id}")
        
        return {
            "success": True,
            "process_id": process_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar documento {process_id}: {str(e)}")
        
        # Marcar como falhado
        db = ctx.get("db")
        if db:
            await db.processes.update_one(
                {"id": process_id},
                {
                    "$set": {
                        "ai_processing_status": "failed",
                        "ai_processing_error": str(e)
                    }
                }
            )
        raise


# ====================================================================
# TAREFAS DE SINCRONIZAÇÃO
# ====================================================================
async def sync_trello_task(
    ctx: Dict[str, Any],
    process_id: str,
    action: str = "sync"
) -> Dict[str, Any]:
    """
    Tarefa para sincronização com Trello.
    
    Actions:
        - sync: Sincronizar estado
        - create_card: Criar cartão
        - update_card: Actualizar cartão
    """
    logger.info(f"📋 Sincronizando Trello: processo={process_id}, action={action}")
    
    try:
        from services.trello import TrelloService
        
        trello = TrelloService()
        
        if action == "sync":
            result = await trello.sync_process(process_id)
        elif action == "create_card":
            result = await trello.create_card_for_process(process_id)
        elif action == "update_card":
            result = await trello.update_card_for_process(process_id)
        else:
            result = {"error": f"Unknown action: {action}"}
        
        logger.info(f"✅ Trello sincronizado: {process_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro na sincronização Trello: {str(e)}")
        raise


# ====================================================================
# TAREFAS DE MANUTENÇÃO (CRON)
# ====================================================================
async def cleanup_temp_files_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tarefa de limpeza de ficheiros temporários.
    Executada periodicamente via cron.
    """
    logger.info("🧹 Iniciando limpeza de ficheiros temporários...")
    
    import os
    import shutil
    from pathlib import Path
    
    temp_dirs = ["/tmp/creditoimo", "/app/backend/temp"]
    files_deleted = 0
    bytes_freed = 0
    
    for temp_dir in temp_dirs:
        if not os.path.exists(temp_dir):
            continue
            
        for item in Path(temp_dir).glob("*"):
            try:
                # Apagar ficheiros com mais de 24 horas
                if item.is_file():
                    age = datetime.now().timestamp() - item.stat().st_mtime
                    if age > 86400:  # 24 horas
                        size = item.stat().st_size
                        item.unlink()
                        files_deleted += 1
                        bytes_freed += size
            except Exception as e:
                logger.warning(f"Não foi possível apagar {item}: {e}")
    
    logger.info(f"✅ Limpeza concluída: {files_deleted} ficheiros, {bytes_freed / 1024:.2f} KB libertados")
    
    return {
        "files_deleted": files_deleted,
        "bytes_freed": bytes_freed
    }


async def generate_daily_report_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tarefa para gerar relatório diário.
    Executada todos os dias às 8:00.
    """
    logger.info("📊 Gerando relatório diário...")
    
    try:
        db = ctx.get("db")
        
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        
        # Contar processos criados ontem
        new_processes = await db.processes.count_documents({
            "created_at": {"$gte": yesterday, "$lt": today}
        })
        
        # Contar processos concluídos ontem
        completed = await db.processes.count_documents({
            "status": "escritura_realizada",
            "updated_at": {"$gte": yesterday, "$lt": today}
        })
        
        report = {
            "date": yesterday.isoformat(),
            "new_processes": new_processes,
            "completed_processes": completed,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"✅ Relatório gerado: {new_processes} novos, {completed} concluídos")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório: {str(e)}")
        raise


async def check_deadlines_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tarefa para verificar prazos próximos e enviar alertas.
    Executada a cada hora.
    """
    logger.info("⏰ Verificando prazos...")
    
    try:
        db = ctx.get("db")
        
        # Encontrar prazos nas próximas 48 horas
        now = datetime.now(timezone.utc)
        deadline_threshold = now + timedelta(hours=48)
        
        deadlines = await db.deadlines.find({
            "due_date": {"$gte": now, "$lte": deadline_threshold},
            "status": {"$ne": "completed"},
            "notified": {"$ne": True}
        }).to_list(100)
        
        alerts_sent = 0
        
        for deadline in deadlines:
            # Criar alerta
            await db.alerts.insert_one({
                "type": "deadline_approaching",
                "process_id": deadline.get("process_id"),
                "deadline_id": str(deadline.get("_id")),
                "message": f"Prazo próximo: {deadline.get('title')}",
                "due_date": deadline.get("due_date"),
                "created_at": now
            })
            
            # Marcar como notificado
            await db.deadlines.update_one(
                {"_id": deadline["_id"]},
                {"$set": {"notified": True}}
            )
            
            alerts_sent += 1
        
        logger.info(f"✅ Verificação de prazos: {alerts_sent} alertas criados")
        
        return {"alerts_sent": alerts_sent}
        
    except Exception as e:
        logger.error(f"❌ Erro na verificação de prazos: {str(e)}")
        raise


# ====================================================================
# TAREFAS GDPR (CONFORMIDADE)
# ====================================================================
async def gdpr_anonymization_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tarefa de anonimização GDPR.
    Executada semanalmente (domingo às 2:00).
    
    Processa processos com:
    - Estado: concluído, desistência, arquivado, etc.
    - Data de actualização > 2 anos (configurável)
    - Ainda não anonimizados
    
    Conforme RGPD Artigo 17 (Direito ao apagamento) e
    Artigo 5(1)(e) (Limitação da conservação).
    """
    logger.info("🔒 [GDPR] Iniciando tarefa de anonimização semanal...")
    
    try:
        from services.gdpr import run_anonymization_batch, get_gdpr_statistics
        
        # Obter estatísticas antes
        stats_before = await get_gdpr_statistics()
        
        # Executar anonimização em lote
        result = await run_anonymization_batch(
            dry_run=False,  # Executar de verdade
            batch_size=100
        )
        
        # Obter estatísticas depois
        stats_after = await get_gdpr_statistics()
        
        # Log detalhado
        logger.info(
            f"🔒 [GDPR] Tarefa concluída:\n"
            f"   - Processados: {result.get('processed', 0)}\n"
            f"   - Sucesso: {result.get('succeeded', 0)}\n"
            f"   - Falhas: {result.get('failed', 0)}\n"
            f"   - Total anonimizados: {stats_after.get('anonymized_processes', 0)}\n"
            f"   - Pendentes: {stats_after.get('eligible_for_anonymization', 0)}"
        )
        
        return {
            "success": True,
            "task": "gdpr_anonymization",
            "processed": result.get("processed", 0),
            "succeeded": result.get("succeeded", 0),
            "failed": result.get("failed", 0),
            "errors": result.get("errors", []),
            "stats": {
                "before": stats_before,
                "after": stats_after
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [GDPR] Erro na tarefa de anonimização: {str(e)}")
        raise


async def gdpr_audit_report_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gera relatório mensal de auditoria GDPR.
    Executada no primeiro dia de cada mês às 6:00.
    """
    logger.info("📊 [GDPR] Gerando relatório de auditoria...")
    
    try:
        from services.gdpr import get_gdpr_statistics
        from database import db
        
        now = datetime.now(timezone.utc)
        last_month = now - timedelta(days=30)
        
        # Estatísticas gerais
        stats = await get_gdpr_statistics()
        
        # Acções de auditoria do último mês
        audit_actions = await db.gdpr_audit.aggregate([
            {"$match": {"timestamp": {"$gte": last_month}}},
            {"$group": {"_id": "$action", "count": {"$sum": 1}}}
        ]).to_list(100)
        
        report = {
            "report_type": "gdpr_monthly_audit",
            "period": {
                "from": last_month.isoformat(),
                "to": now.isoformat()
            },
            "statistics": stats,
            "audit_actions": {item["_id"]: item["count"] for item in audit_actions},
            "generated_at": now.isoformat()
        }
        
        # Guardar relatório
        await db.gdpr_reports.insert_one(report)
        
        logger.info(f"📊 [GDPR] Relatório gerado: {stats.get('anonymized_processes', 0)} anonimizados")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ [GDPR] Erro ao gerar relatório: {str(e)}")
        raise


# ====================================================================
# TAREFAS DE BACKUP
# ====================================================================
async def database_backup_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tarefa de backup diário da base de dados.
    Executada todos os dias às 03:00.
    
    Workflow:
    1. Criar backup com mongodump
    2. Comprimir em ZIP
    3. Upload para OneDrive (se configurado)
    4. Limpar backups antigos
    """
    logger.info("🗄️ [BACKUP] Iniciando backup diário...")
    
    try:
        from services.backup import full_backup_workflow, get_backup_statistics
        
        # Executar workflow completo
        result = await full_backup_workflow(
            upload_to_cloud=True,
            cleanup_after=True
        )
        
        # Log resultado
        if result["success"]:
            backup_info = result.get("backup", {})
            upload_info = result.get("upload", {})
            
            logger.info(
                f"✅ [BACKUP] Concluído com sucesso:\n"
                f"   - Ficheiro: {backup_info.get('filename', 'N/A')}\n"
                f"   - Tamanho: {backup_info.get('size_mb', 0)}MB\n"
                f"   - Duração: {backup_info.get('duration_seconds', 0)}s\n"
                f"   - OneDrive: {'✅' if upload_info.get('success') else '❌'}"
            )
            
            # Obter estatísticas
            stats = await get_backup_statistics()
            logger.info(
                f"📊 [BACKUP] Stats: {stats['successful']}/{stats['total_backups']} "
                f"bem sucedidos ({stats['success_rate']}%)"
            )
        else:
            logger.error(f"❌ [BACKUP] Falhou: {result.get('error', 'Erro desconhecido')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [BACKUP] Erro na tarefa de backup: {str(e)}")
        raise


async def backup_verification_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tarefa de verificação semanal dos backups.
    Executada às segundas às 09:00.
    
    Verifica:
    - Último backup bem sucedido
    - Espaço em disco
    - Integridade dos ficheiros
    """
    logger.info("🔍 [BACKUP] Verificando integridade dos backups...")
    
    try:
        from services.backup import get_backup_statistics, config
        import zipfile
        
        stats = await get_backup_statistics()
        issues = []
        
        # Verificar último backup
        last_backup = stats.get("last_backup")
        if not last_backup:
            issues.append("Nenhum backup encontrado no histórico")
        elif not last_backup.get("success"):
            issues.append(f"Último backup falhou: {last_backup.get('error', 'N/A')}")
        
        # Verificar idade do último backup
        if last_backup and last_backup.get("started_at"):
            last_backup_time = datetime.fromisoformat(
                last_backup["started_at"].replace("Z", "+00:00")
            )
            age_hours = (datetime.now(timezone.utc) - last_backup_time).total_seconds() / 3600
            
            if age_hours > 48:
                issues.append(f"Último backup tem {age_hours:.0f} horas (>48h)")
        
        # Verificar integridade dos ZIPs locais
        corrupted = []
        for backup_file in config.BACKUP_DIR.glob("backup_*.zip"):
            try:
                with zipfile.ZipFile(backup_file, 'r') as zf:
                    if zf.testzip() is not None:
                        corrupted.append(backup_file.name)
            except Exception as e:
                corrupted.append(f"{backup_file.name}: {str(e)}")
        
        if corrupted:
            issues.append(f"Backups corrompidos: {', '.join(corrupted)}")
        
        result = {
            "success": len(issues) == 0,
            "statistics": stats,
            "issues": issues,
            "verified_at": datetime.now(timezone.utc).isoformat()
        }
        
        if issues:
            logger.warning(f"⚠️ [BACKUP] Problemas encontrados: {issues}")
        else:
            logger.info("✅ [BACKUP] Verificação concluída sem problemas")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [BACKUP] Erro na verificação: {str(e)}")
        raise


# ====================================================================
# ARQ WORKER SETTINGS
# ====================================================================
class WorkerSettings:
    """
    Configuração do Worker ARQ.
    
    Para executar: arq worker.WorkerSettings
    """
    
    # Funções disponíveis para o worker
    functions = [
        # Email
        send_email_task,
        send_registration_email_task,
        
        # IA/Documentos
        process_ai_document_task,
        
        # Sincronização
        sync_trello_task,
        
        # Manutenção
        cleanup_temp_files_task,
        generate_daily_report_task,
        check_deadlines_task,
        
        # GDPR / Conformidade
        gdpr_anonymization_task,
        gdpr_audit_report_task,
        
        # Backup
        database_backup_task,
        backup_verification_task,
    ]
    
    # Tarefas agendadas (cron)
    cron_jobs = [
        # Limpeza de ficheiros às 3:00 todos os dias
        cron(cleanup_temp_files_task, hour=3, minute=0),
        
        # Relatório diário às 8:00
        cron(generate_daily_report_task, hour=8, minute=0),
        
        # Verificar prazos a cada hora
        cron(check_deadlines_task, minute=0),
        
        # GDPR: Anonimização semanal (domingo às 2:00)
        cron(gdpr_anonymization_task, weekday=6, hour=2, minute=0),
        
        # GDPR: Relatório de auditoria mensal (dia 1 às 6:00)
        cron(gdpr_audit_report_task, day=1, hour=6, minute=0),
    ]
    
    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    
    # Configuração Redis
    redis_settings = get_redis_settings()
    
    # Configurações do worker
    max_jobs = TASK_MAX_JOBS
    job_timeout = TASK_JOB_TIMEOUT
    max_tries = TASK_MAX_TRIES
    retry_jobs = True
    
    # Health check
    health_check_interval = 30
    
    # Logging
    log_results = True


# ====================================================================
# UTILITÁRIO PARA ENQUEUE
# ====================================================================
async def get_task_queue() -> ArqRedis:
    """Obtém conexão à fila de tarefas."""
    from arq import create_pool
    return await create_pool(get_redis_settings())


# Instância global (lazy loading)
_task_queue: Optional[ArqRedis] = None


async def enqueue_task(
    function_name: str,
    *args,
    _queue_name: Optional[str] = None,
    _defer_by: Optional[timedelta] = None,
    _defer_until: Optional[datetime] = None,
    **kwargs
) -> Optional[str]:
    """
    Enfileira uma tarefa para execução em background.
    
    Args:
        function_name: Nome da função (ex: 'send_email_task')
        *args: Argumentos posicionais
        _queue_name: Nome da fila (opcional)
        _defer_by: Atrasar execução por X tempo
        _defer_until: Agendar para data/hora específica
        **kwargs: Argumentos nomeados
    
    Returns:
        Job ID se sucesso, None se falhar
    """
    global _task_queue
    
    try:
        if _task_queue is None:
            _task_queue = await get_task_queue()
        
        job = await _task_queue.enqueue_job(
            function_name,
            *args,
            _queue_name=_queue_name,
            _defer_by=_defer_by,
            _defer_until=_defer_until,
            **kwargs
        )
        
        logger.info(f"📤 Tarefa enfileirada: {function_name} (job_id={job.job_id})")
        return job.job_id
        
    except Exception as e:
        logger.error(f"❌ Erro ao enfileirar tarefa {function_name}: {str(e)}")
        return None


# ====================================================================
# EXECUÇÃO DIRETA (para debug)
# ====================================================================
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("ARQ WORKER - CREDITOIMO")
    print("=" * 60)
    print()
    print("Para executar o worker, use:")
    print("  cd /app/backend && arq worker.WorkerSettings")
    print()
    print("Com logs verbose:")
    print("  cd /app/backend && arq worker.WorkerSettings --verbose")
    print()
    print("Tarefas disponíveis:")
    for func in WorkerSettings.functions:
        print(f"  - {func.__name__}")
    print()
    print("Tarefas agendadas (cron):")
    for cron_job in WorkerSettings.cron_jobs:
        print(f"  - {cron_job}")
    print("=" * 60)
