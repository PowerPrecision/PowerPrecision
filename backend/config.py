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
# CORS CONFIG
# ====================================================================
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')


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
