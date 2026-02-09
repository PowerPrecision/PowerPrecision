"""
====================================================================
RATE LIMITING MIDDLEWARE - ENTERPRISE SECURITY
====================================================================
Protecção contra:
- Ataques de força bruta (brute force)
- Negação de serviço (DDoS)
- Spam de registos
- Abuso de APIs públicas

Usa SlowAPI com limites restritivos para produção.
====================================================================
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    """
    Obtém o IP real do cliente, considerando proxies e load balancers.
    Verifica headers X-Forwarded-For e X-Real-IP antes de usar o IP directo.
    """
    # Verificar X-Forwarded-For (pode ter múltiplos IPs separados por vírgula)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # O primeiro IP é o cliente original
        client_ip = forwarded_for.split(",")[0].strip()
        return client_ip
    
    # Verificar X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback para o IP directo
    return get_remote_address(request)


# Criar instância do Limiter com identificação correcta de IP
limiter = Limiter(key_func=_get_client_ip)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Handler para erro 429 - Too Many Requests.
    Retorna resposta JSON estruturada com detalhes do limite excedido.
    """
    client_ip = _get_client_ip(request)
    logger.warning(f"Rate limit excedido para IP {client_ip}: {request.url.path}")
    
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "rate_limit_exceeded",
            "message": "Demasiados pedidos. Tente novamente mais tarde.",
            "detail": str(exc.detail),
            "retry_after_seconds": _parse_retry_after(exc.detail)
        },
        headers={
            "Retry-After": str(_parse_retry_after(exc.detail)),
            "X-RateLimit-Limit": str(exc.detail)
        }
    )


def _parse_retry_after(limit_detail: str) -> int:
    """
    Calcula o tempo de espera em segundos baseado no limite.
    Ex: "5 per 1 hour" -> 3600 segundos
    """
    try:
        if "hour" in str(limit_detail):
            return 3600
        elif "minute" in str(limit_detail):
            return 60
        elif "day" in str(limit_detail):
            return 86400
        elif "second" in str(limit_detail):
            return 1
        return 60  # Default: 1 minuto
    except Exception:
        return 60


# ====================================================================
# RATE LIMITS - CONFIGURAÇÃO ENTERPRISE
# ====================================================================
# Limites restritivos para prevenir abusos em produção
# ====================================================================
RATE_LIMITS = {
    # Rotas públicas - MUITO restritivas (anti-spam)
    "client_registration": "5/hour",      # 5 registos por hora por IP
    "public_health": "60/minute",         # Health checks
    
    # Autenticação - Restritivas (anti-brute-force)
    "login": "10/minute",                 # 10 tentativas por minuto
    "register": "3/hour",                 # 3 registos por hora
    "password_reset": "3/hour",           # 3 resets por hora
    
    # APIs autenticadas - Moderadas
    "api_default": "100/minute",          # Default para APIs
    "api_write": "30/minute",             # Operações de escrita
    "api_upload": "10/minute",            # Uploads de ficheiros
    
    # APIs administrativas - Menos restritivas
    "admin_api": "200/minute",            # APIs de admin
}
