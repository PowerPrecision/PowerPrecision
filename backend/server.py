"""
====================================================================
CREDITOIMO - BACKEND SERVER
====================================================================
Sistema de Gestão de Processos de Crédito Habitação

Observabilidade: Sentry SDK para error tracking e performance monitoring
====================================================================
"""
import logging
import uuid
from datetime import datetime, timezone

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.pymongo import PyMongoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from fastapi import FastAPI, Request
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
from models.auth import UserRole
from services.auth import hash_password
from middleware.rate_limit import limiter
from routes import (
    auth_router, processes_router, admin_router, users_router,
    deadlines_router, activities_router, onedrive_router,
    public_router, stats_router, ai_router, documents_router
)
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


# ====================================================================
# SENTRY INITIALIZATION (antes de qualquer outra coisa)
# ====================================================================
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        
        # Performance Monitoring
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        
        # Integrações
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            PyMongoIntegration(),
            LoggingIntegration(
                level=logging.INFO,        # Capturar logs INFO+ como breadcrumbs
                event_level=logging.ERROR  # Enviar logs ERROR+ como eventos
            ),
        ],
        
        # Configurações de privacidade
        send_default_pii=SENTRY_SEND_DEFAULT_PII,
        
        # Filtrar eventos
        before_send=_sentry_before_send,
        
        # Release tracking (usar em CI/CD)
        release=f"creditoimo@{datetime.now().strftime('%Y.%m.%d')}",
        
        # Attach stack trace to messages
        attach_stacktrace=True,
        
        # Enable debug mode in development
        debug=SENTRY_ENVIRONMENT == "development",
    )


def _sentry_before_send(event, hint):
    """
    Hook para filtrar/modificar eventos antes de enviar ao Sentry.
    Útil para remover dados sensíveis ou ignorar erros específicos.
    """
    # Ignorar erros de rate limiting (são esperados)
    if "exception" in event:
        exc_type = event.get("exception", {}).get("values", [{}])[0].get("type", "")
        if exc_type in ["RateLimitExceeded"]:
            return None
    
    # Remover dados sensíveis de headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[FILTERED]"
    
    return event


# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = FastAPI(title="Sistema de Gestão de Processos")

# Configurar Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Include all routers under /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(public_router, prefix="/api")
app.include_router(processes_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(deadlines_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(onedrive_router, prefix="/api")
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


# Health check endpoint for Kubernetes
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
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
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.processes.create_index("id", unique=True)
    await db.processes.create_index("client_id")
    await db.deadlines.create_index("id", unique=True)
    await db.deadlines.create_index("process_id")
    await db.activities.create_index("process_id")
    await db.history.create_index("process_id")
    await db.workflow_statuses.create_index("name", unique=True)
    
    # Indexes para a colecção de notificações
    await db.notifications.create_index("id", unique=True)
    await db.notifications.create_index("user_id")
    await db.notifications.create_index("process_id")
    
    # Indexes para imóveis angariados
    await db.properties.create_index("id", unique=True)
    await db.properties.create_index("internal_reference", unique=True, sparse=True)
    await db.properties.create_index("status")
    await db.properties.create_index("address.district")
    await db.properties.create_index("financials.asking_price")
    await db.notifications.create_index("created_at")
    await db.notifications.create_index([("user_id", 1), ("read", 1)])  # Index composto para queries
    
    # Indexes para push subscriptions
    await db.push_subscriptions.create_index("id", unique=True)
    await db.push_subscriptions.create_index("user_id")
    await db.push_subscriptions.create_index("endpoint", unique=True)
    await db.push_subscriptions.create_index([("user_id", 1), ("is_active", 1)])
    
    # Indexes para tarefas
    await db.tasks.create_index("id", unique=True)
    await db.tasks.create_index("process_id")
    await db.tasks.create_index("created_by")
    await db.tasks.create_index("assigned_to")
    await db.tasks.create_index([("completed", 1), ("created_at", -1)])
    
    # Indexes para clientes
    await db.clients.create_index("id", unique=True)
    await db.clients.create_index("nome")
    await db.clients.create_index("contacto.email", sparse=True)
    await db.clients.create_index("dados_pessoais.nif", sparse=True)
    await db.clients.create_index("process_ids")
    
    # Indexes para emails
    await db.emails.create_index("id", unique=True)
    await db.emails.create_index("process_id")
    await db.emails.create_index([("process_id", 1), ("sent_at", -1)])
    await db.emails.create_index("direction")
    
    # Create default workflow statuses if none exist - 15 fases do Trello
    status_count = await db.workflow_statuses.count_documents({})
    if status_count == 0:
        default_statuses = [
            {"id": str(uuid.uuid4()), "name": "clientes_espera", "label": "Clientes em Espera", "order": 1, "color": "yellow", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "fase_documental", "label": "Fase Documental", "order": 2, "color": "blue", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "entregue_intermediarios", "label": "Entregue aos Intermediários", "order": 3, "color": "indigo", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "enviado_bruno", "label": "Enviado ao Bruno", "order": 4, "color": "purple", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "enviado_luis", "label": "Enviado ao Luís", "order": 5, "color": "purple", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "enviado_bcp_rui", "label": "Enviado BCP Rui", "order": 6, "color": "purple", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "entradas_precision", "label": "Entradas Precision", "order": 7, "color": "orange", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "fase_bancaria", "label": "Fase Bancária - Pré Aprovação", "order": 8, "color": "orange", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "fase_visitas", "label": "Fase de Visitas", "order": 9, "color": "blue", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "ch_aprovado", "label": "CH Aprovado - Avaliação", "order": 10, "color": "green", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "fase_escritura", "label": "Fase de Escritura", "order": 11, "color": "green", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "escritura_agendada", "label": "Escritura Agendada", "order": 12, "color": "green", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "concluidos", "label": "Concluídos", "order": 13, "color": "green", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "desistencias", "label": "Desistências", "order": 14, "color": "red", "is_default": True},
        ]
        await db.workflow_statuses.insert_many(default_statuses)
        logger.info("14 workflow statuses created (conforme Trello)")
    
    # NOTA: Utilizadores iniciais são criados via script seed.py
    # Para criar utilizadores: cd /app/backend && python seed.py
    user_count = await db.users.count_documents({})
    if user_count == 0:
        logger.warning("Nenhum utilizador encontrado! Execute 'python seed.py' para criar utilizadores iniciais.")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
