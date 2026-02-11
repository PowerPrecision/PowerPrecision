import os
import logging
from datetime import datetime, timezone
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.pymongo import PyMongoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import (
    CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, 
    CORS_ALLOW_HEADERS, CORS_MAX_AGE,
    SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE,
    SENTRY_PROFILES_SAMPLE_RATE, SENTRY_SEND_DEFAULT_PII
)
from database import db, client
from middleware.rate_limit import limiter
from routes import (
    auth_router, processes_router, admin_router, users_router,
    deadlines_router, activities_router,
    public_router, stats_router, ai_router, documents_router
)
# Outras rotas
from routes.alerts import router as alerts_router
from routes.websocket import router as websocket_router
from routes.push_notifications import router as push_notifications_router
from routes.tasks import router as tasks_router
from routes.emails import router as emails_router
from routes.trello import router as trello_router
from routes.ai_bulk import router as ai_bulk_router
from routes.leads import router as leads_router
from routes.match import router as match_router
from routes.system_config import router as system_config_router
from routes.properties import router as properties_router
from routes.clients import router as clients_router
from routes.gdpr import router as gdpr_router
from routes.backup import router as backup_router
from routes.scraper import router as scraper_router
from routes.minutas import router as minutas_router
from routes.ai_agent import router as ai_agent_router

# Configuração Sentry
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            PyMongoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=SENTRY_SEND_DEFAULT_PII,
        attach_stacktrace=True,
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sistema de Gestão de Processos")

# CONFIGURAÇÃO DE RATE LIMIT
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORREÇÃO: Se estiver em testes, desativar o limitador completamente
if os.getenv("TESTING") == "true":
    limiter.enabled = False

# Rotas
app.include_router(auth_router, prefix="/api")
app.include_router(public_router, prefix="/api")
app.include_router(processes_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(deadlines_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")
app.include_router(push_notifications_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(emails_router, prefix="/api")
app.include_router(trello_router, prefix="/api")
app.include_router(ai_bulk_router, prefix="/api")
app.include_router(leads_router, prefix="/api")
app.include_router(match_router, prefix="/api")
app.include_router(system_config_router, prefix="/api")
app.include_router(properties_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(gdpr_router, prefix="/api")
app.include_router(backup_router, prefix="/api")
app.include_router(scraper_router, prefix="/api")
app.include_router(minutas_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

app.add_middleware(
    CORSMiddleware,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_origins=CORS_ORIGINS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    max_age=CORS_MAX_AGE,
)

@app.on_event("startup")
async def startup():
    logger.info("🚀 Iniciando aplicação...")
    # Tenta conectar Redis sem falhar a app se não existir
    try:
        from services.task_queue import task_queue
        await task_queue.connect()
    except Exception:
        pass 

@app.on_event("shutdown")
async def shutdown_db_client():
    # CORREÇÃO CRÍTICA: Não fechar a conexão DB se estivermos a correr testes!
    # O pytest reutiliza a conexão global, se a fecharmos aqui, o próximo teste falha.
    if os.getenv("TESTING") == "true":
        return
        
    try:
        client.close()
    except Exception:
        pass