import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')


# ====================================================================
# VALIDAÇÃO DE VARIÁVEIS DE AMBIENTE CRÍTICAS
# ====================================================================
def get_required_env(key: str) -> str:
    """Obter variável de ambiente obrigatória. Falha se não existir."""
    value = os.environ.get(key)
    if not value:
        print(f"❌ ERRO FATAL: Variável de ambiente '{key}' não definida!", file=sys.stderr)
        print(f"   Configure no ficheiro .env ou nas variáveis de ambiente do sistema.", file=sys.stderr)
        sys.exit(1)
    return value


# ====================================================================
# JWT CONFIG (OBRIGATÓRIO)
# ====================================================================
JWT_SECRET = get_required_env('JWT_SECRET')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Verificar se não é a chave padrão de exemplo
if 'change-in-production' in JWT_SECRET or JWT_SECRET == 'super-secret-key':
    print("⚠️  AVISO: JWT_SECRET parece ser um valor de exemplo. Altere em produção!", file=sys.stderr)


# ====================================================================
# DATABASE CONFIG (OBRIGATÓRIO)
# ====================================================================
MONGO_URL = get_required_env('MONGO_URL')
DB_NAME = get_required_env('DB_NAME')


# ====================================================================
# CORS CONFIG (ESTRITO)
# ====================================================================
# CORS_ORIGINS deve ser definido explicitamente em produção
# Formato: "https://domain1.com,https://domain2.com"
# Em desenvolvimento pode usar "*" mas NÃO em produção
_cors_env = os.environ.get('CORS_ORIGINS', '').strip().strip('"').strip("'")

# Validação estrita de CORS
if not _cors_env:
    print("⚠️  AVISO: CORS_ORIGINS não definido. Usando wildcard (*) - NÃO usar em produção!", file=sys.stderr)
    CORS_ORIGINS = ["*"]
elif _cors_env == '*':
    print("⚠️  AVISO: CORS_ORIGINS definido como '*' - NÃO usar em produção!", file=sys.stderr)
    CORS_ORIGINS = ["*"]
else:
    # Parsing e validação das origens
    CORS_ORIGINS = []
    for origin in _cors_env.split(','):
        origin = origin.strip()
        if origin:
            # Validar formato da origem (deve ser URL válido)
            if origin.startswith('http://') or origin.startswith('https://'):
                CORS_ORIGINS.append(origin)
            else:
                print(f"⚠️  AVISO: Origem CORS inválida ignorada: {origin}", file=sys.stderr)
    
    if not CORS_ORIGINS:
        print("❌ ERRO: Nenhuma origem CORS válida configurada!", file=sys.stderr)
        CORS_ORIGINS = ["*"]
    else:
        print(f"✅ CORS configurado para: {', '.join(CORS_ORIGINS)}", file=sys.stderr)

# Configurações adicionais de CORS
CORS_ALLOW_CREDENTIALS = os.environ.get('CORS_ALLOW_CREDENTIALS', 'true').lower() == 'true'
CORS_ALLOW_METHODS = os.environ.get('CORS_ALLOW_METHODS', 'GET,POST,PUT,DELETE,OPTIONS,PATCH').split(',')
CORS_ALLOW_HEADERS = os.environ.get('CORS_ALLOW_HEADERS', 'Authorization,Content-Type,Accept,Origin,X-Requested-With').split(',')
CORS_MAX_AGE = int(os.environ.get('CORS_MAX_AGE', '600'))


# ====================================================================
# OneDrive Config (opcional)
# ====================================================================
ONEDRIVE_TENANT_ID = os.environ.get('ONEDRIVE_TENANT_ID', '')
ONEDRIVE_CLIENT_ID = os.environ.get('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_CLIENT_SECRET = os.environ.get('ONEDRIVE_CLIENT_SECRET', '')
ONEDRIVE_BASE_PATH = os.environ.get('ONEDRIVE_BASE_PATH', 'Documentação Clientes')


# ====================================================================
# EMAIL CONFIG (opcional)
# ====================================================================
SMTP_SERVER = os.environ.get('SMTP_SERVER', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')


# ====================================================================
# TRELLO CONFIG (opcional - para integração futura)
# ====================================================================
TRELLO_API_KEY = os.environ.get('TRELLO_API_KEY', '')
TRELLO_TOKEN = os.environ.get('TRELLO_TOKEN', '')
TRELLO_BOARD_ID = os.environ.get('TRELLO_BOARD_ID', '')
