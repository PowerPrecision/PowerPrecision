from slowapi import Limiter
from slowapi.util import get_remote_address

# Criar uma instância ÚNICA do limiter para ser partilhada
limiter = Limiter(key_func=get_remote_address)