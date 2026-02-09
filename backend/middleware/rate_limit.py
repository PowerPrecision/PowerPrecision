"""
Rate Limiting Middleware usando SlowAPI
Protege rotas públicas contra ataques de força bruta e DDoS.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse


# Criar instância do Limiter usando o IP do cliente como chave
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handler personalizado para quando o rate limit é excedido."""
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "rate_limit_exceeded",
            "message": "Demasiados pedidos. Tente novamente mais tarde.",
            "retry_after": exc.detail
        }
    )


# Rate limits configuráveis
RATE_LIMITS = {
    # Rotas de autenticação - mais restritivas
    "login": "5/minute",
    "register": "3/minute",
    
    # Rotas públicas
    "client_registration": "3/minute",
    "public_health": "30/minute",
    
    # Rotas gerais (default)
    "default": "60/minute"
}
