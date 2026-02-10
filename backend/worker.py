import os
import sys
import logging
import asyncio
import signal
import time
import tempfile
from datetime import datetime, timezone, timedelta

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("worker")

# Adicionar caminho do backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import db
    from services.task_queue import task_queue
    from services.scheduled_tasks import (
        check_deadlines,
        check_document_expiries,
        cleanup_old_logs
    )
    from services.trello import trello_service
    from services.email_service import email_service
    from services.scraper import scrape_property_url
    from services.client_match import match_leads_to_clients
except ImportError as e:
    logger.error(f"Erro ao importar módulos: {e}")
    sys.exit(1)

# Flag para paragem graciosa
shutdown_event = asyncio.Event()

async def process_task(task: dict):
    """
    Processa uma tarefa individual da fila.
    """
    task_id = task.get("id")
    task_type = task.get("type")
    payload = task.get("payload", {})
    
    logger.info(f"Processando tarefa {task_id} ({task_type})")
    
    try:
        start_time = time.time()
        result = None
        
        if task_type == "scrape_property":
            url = payload.get("url")
            if url:
                result = await scrape_property_url(url)
                # Se for lead, atualizar dados
                lead_id = payload.get("lead_id")
                if lead_id and result:
                    await db.property_leads.update_one(
                        {"id": lead_id},
                        {"$set": {
                            "title": result.get("titulo"),
                            "price": result.get("preco"),
                            "location": result.get("localizacao"),
                            "scraped_data": result,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
        
        elif task_type == "match_leads":
            # Executar matching de leads com clientes
            result = await match_leads_to_clients()
            
        elif task_type == "send_email":
            # Enviar email assíncrono
            to_email = payload.get("to")
            subject = payload.get("subject")
            content = payload.get("content")
            if to_email and subject and content:
                result = await email_service.send_email(to_email, subject, content)
                
        elif task_type == "sync_trello":
            # Sincronização periódica com Trello
            result = await trello_service.sync_board()
            
        else:
            logger.warning(f"Tipo de tarefa desconhecido: {task_type}")
            result = {"error": "Unknown task type"}
            
        # Marcar como concluída
        duration = time.time() - start_time
        await task_queue.complete_task(task_id, result=result)
        logger.info(f"Tarefa {task_id} concluída em {duration:.2f}s")
        
    except Exception as e:
        logger.error(f"Erro ao processar tarefa {task_id}: {e}", exc_info=True)
        await task_queue.fail_task(task_id, error=str(e))

async def worker_loop():
    """
    Loop principal do worker.
    Verifica e processa tarefas da fila.
    """
    logger.info("Worker iniciado. Aguardando tarefas...")
    
    while not shutdown_event.is_set():
        try:
            # Buscar próxima tarefa pendente
            task = await task_queue.get_next_task()
            
            if task:
                await process_task(task)
            else:
                # Se não há tarefas, esperar um pouco
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Erro no loop do worker: {e}")
            await asyncio.sleep(5) # Esperar antes de tentar novamente

async def scheduler_loop():
    """
    Loop para tarefas agendadas (Cron jobs).
    """
    logger.info("Agendador iniciado.")
    
    # Horários da última execução
    last_runs = {
        "deadlines": 0,
        "expiries": 0,
        "cleanup": 0,
        "matching": 0
    }
    
    while not shutdown_event.is_set():
        try:
            now = time.time()
            
            # Verificar prazos (a cada 1 hora)
            if now - last_runs["deadlines"] > 3600:
                logger.info("Executando verificação de prazos...")
                await check_deadlines()
                last_runs["deadlines"] = now
                
            # Verificar validade de documentos (a cada 24 horas - simplificado para teste 1h)
            if now - last_runs["expiries"] > 3600:
                logger.info("Executando verificação de documentos...")
                await check_document_expiries()
                last_runs["expiries"] = now
                
            # Limpeza de logs e temporários (a cada 24 horas)
            if now - last_runs["cleanup"] > 86400:
                logger.info("Executando limpeza...")
                await cleanup_old_logs()
                await cleanup_temp_files()
                last_runs["cleanup"] = now

            # Matching automático de Leads (a cada 30 minutos)
            if now - last_runs["matching"] > 1800:
                logger.info("Executando matching automático...")
                await task_queue.add_task("match_leads", {})
                last_runs["matching"] = now
            
            await asyncio.sleep(60) # Verificar a cada minuto
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Erro no agendador: {e}")
            await asyncio.sleep(60)

async def cleanup_temp_files():
    """Limpa ficheiros temporários antigos."""
    logger.info("A executar limpeza de ficheiros temporários...")
    
    # CORREÇÃO DE SEGURANÇA: Usar caminhos dinâmicos
    sys_temp = tempfile.gettempdir()
    
    # Lista de diretorias a limpar
    temp_dirs = [
        os.path.join(sys_temp, "creditoimo"),
        os.path.join(os.getcwd(), "backend", "temp") # Caminho relativo seguro
    ]
    
    files_deleted = 0
    
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            try:
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        # Se ficheiro tem mais de 24h
                        if os.path.isfile(file_path):
                            if time.time() - os.path.getmtime(file_path) > 86400:
                                os.remove(file_path)
                                files_deleted += 1
                    except Exception as e:
                        logger.warning(f"Erro ao apagar {file_path}: {e}")
            except Exception as e:
                logger.warning(f"Erro ao listar {temp_dir}: {e}")
                
    logger.info(f"Limpeza concluída. {files_deleted} ficheiros removidos.")

def handle_shutdown(signum, frame):
    """Handler para sinais de paragem."""
    logger.info("Sinal de paragem recebido. A terminar graciosamente...")
    shutdown_event.set()

async def main():
    # Registar handlers de sinais (SIGINT, SIGTERM)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_async()))

    # Iniciar tarefas concorrentes
    worker_task = asyncio.create_task(worker_loop())
    scheduler_task = asyncio.create_task(scheduler_loop())
    
    # Aguardar sinal de paragem
    await shutdown_event.wait()
    
    # Aguardar finalização das tarefas
    worker_task.cancel()
    scheduler_task.cancel()
    try:
        await asyncio.gather(worker_task, scheduler_task)
    except asyncio.CancelledError:
        pass
        
    logger.info("Worker desligado.")

async def shutdown_async():
    shutdown_event.set()

if __name__ == "__main__":
    asyncio.run(main())