"""
====================================================================
TASK QUEUE CONFIGURATION - CREDITOIMO
====================================================================
Configuração centralizada para o sistema de filas de tarefas (ARQ + Redis).

ARQ é uma biblioteca async para task queues que usa Redis como backend.
Vantagens sobre BackgroundTasks do FastAPI:
- Persistência: tarefas sobrevivem a restarts
- Retry automático com backoff exponencial
- Agendamento de tarefas (cron jobs)
- Monitorização e health checks
- Múltiplos workers para escalar horizontalmente

CONFIGURAÇÃO:
- REDIS_URL: URL de conexão ao Redis
- REDIS_MAX_CONNECTIONS: Pool de conexões
- TASK_* variáveis para timeouts e retries

====================================================================
"""
import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ====================================================================
# REDIS CONFIGURATION
# ====================================================================
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
REDIS_MAX_CONNECTIONS = int(os.environ.get("REDIS_MAX_CONNECTIONS", "10"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

# Parse Redis URL para componentes
def parse_redis_url(url: str) -> dict:
    """Parse Redis URL para host, port, password, db."""
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 6379,
        "password": parsed.password,
        "database": int(parsed.path.lstrip("/") or REDIS_DB),
    }


# ====================================================================
# TASK QUEUE SETTINGS
# ====================================================================
@dataclass
class TaskQueueSettings:
    """Configurações da fila de tarefas."""
    
    # Timeouts (em segundos)
    job_timeout: int = 300          # 5 minutos por tarefa
    job_max_tries: int = 3          # Máximo de tentativas
    job_retry_delay: int = 60       # Delay entre retries (segundos)
    
    # Health check
    health_check_interval: int = 30  # Intervalo de health check
    
    # Queue names
    default_queue: str = "arq:queue"
    high_priority_queue: str = "arq:queue:high"
    low_priority_queue: str = "arq:queue:low"
    
    # Worker settings
    max_jobs: int = 10              # Jobs em paralelo por worker
    poll_delay: float = 0.5         # Delay entre polls


# Instância global de settings
task_settings = TaskQueueSettings(
    job_timeout=int(os.environ.get("TASK_JOB_TIMEOUT", "300")),
    job_max_tries=int(os.environ.get("TASK_MAX_TRIES", "3")),
    job_retry_delay=int(os.environ.get("TASK_RETRY_DELAY", "60")),
    max_jobs=int(os.environ.get("TASK_MAX_JOBS", "10")),
)


# ====================================================================
# ARQ REDIS SETTINGS
# ====================================================================
def get_redis_settings():
    """Retorna configuração Redis para ARQ."""
    from arq.connections import RedisSettings
    
    redis_config = parse_redis_url(REDIS_URL)
    
    return RedisSettings(
        host=redis_config["host"],
        port=redis_config["port"],
        password=redis_config["password"],
        database=redis_config["database"],
        conn_timeout=30,
        conn_retries=5,
        conn_retry_delay=1,
    )


# Log de configuração
logger.info(f"Task Queue configurada: Redis={REDIS_URL.split('@')[-1] if '@' in REDIS_URL else REDIS_URL}")
