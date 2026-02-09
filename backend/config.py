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
# CORS CONFIG (FAIL-SECURE)
# ====================================================================
# CORS_ORIGINS é OBRIGATÓRIO em produção.
# Formato: "https://domain1.com,https://domain2.com"
# A aplicação FALHA se não estiver correctamente configurado.
# ====================================================================
_cors_env = os.environ.get('CORS_ORIGINS', '').strip().strip('"').strip("'")

# FAIL-SECURE: A aplicação DEVE falhar se CORS não estiver configurado
if not _cors_env:
    raise ValueError(
        "❌ ERRO FATAL: CORS_ORIGINS não definido!\n"
        "   Configure a variável de ambiente CORS_ORIGINS com as origens permitidas.\n"
        "   Exemplo: CORS_ORIGINS='https://meusite.com,https://app.meusite.com'\n"
        "   A aplicação não pode arrancar sem configuração CORS explícita."
    )

if _cors_env == '*':
    raise ValueError(
        "❌ ERRO FATAL: CORS_ORIGINS='*' não é permitido!\n"
        "   Wildcards não são aceites em modo de produção.\n"
        "   Configure origens específicas: CORS_ORIGINS='https://meusite.com'"
    )

# Parsing e validação estrita das origens
CORS_ORIGINS = []
_invalid_origins = []

for origin in _cors_env.split(','):
    origin = origin.strip()
    if not origin:
        continue
    
    # Validar formato da origem (deve ser URL válido com protocolo)
    if origin.startswith('https://'):
        CORS_ORIGINS.append(origin)
    elif origin.startswith('http://localhost') or origin.startswith('http://127.0.0.1'):
        # Permitir localhost apenas para desenvolvimento
        print(f"⚠️  AVISO: Origem HTTP localhost permitida (apenas dev): {origin}", file=sys.stderr)
        CORS_ORIGINS.append(origin)
    elif origin.startswith('http://'):
        _invalid_origins.append(f"{origin} (HTTP não seguro)")
    else:
        _invalid_origins.append(f"{origin} (formato inválido)")

# Reportar origens inválidas
if _invalid_origins:
    print(f"⚠️  Origens CORS ignoradas: {', '.join(_invalid_origins)}", file=sys.stderr)

# FAIL-SECURE: Deve haver pelo menos uma origem válida
if not CORS_ORIGINS:
    raise ValueError(
        f"❌ ERRO FATAL: Nenhuma origem CORS válida configurada!\n"
        f"   Origens rejeitadas: {', '.join(_invalid_origins) if _invalid_origins else 'nenhuma fornecida'}\n"
        f"   Use HTTPS para origens de produção: CORS_ORIGINS='https://meusite.com'"
    )

print(f"✅ CORS configurado (fail-secure): {', '.join(CORS_ORIGINS)}", file=sys.stderr)

# Configurações adicionais de CORS (com defaults seguros)
CORS_ALLOW_CREDENTIALS = os.environ.get('CORS_ALLOW_CREDENTIALS', 'true').lower() == 'true'
CORS_ALLOW_METHODS = os.environ.get('CORS_ALLOW_METHODS', 'GET,POST,PUT,DELETE,OPTIONS,PATCH').split(',')
CORS_ALLOW_HEADERS = os.environ.get('CORS_ALLOW_HEADERS', 'Authorization,Content-Type,Accept,Origin,X-Requested-With').split(',')
CORS_MAX_AGE = int(os.environ.get('CORS_MAX_AGE', '600'))


# ====================================================================
# SENTRY CONFIG (OBSERVABILIDADE)
# ====================================================================
# SENTRY_DSN é opcional - se não definido, Sentry fica desactivado
# Obter DSN em: https://sentry.io -> Project Settings -> Client Keys (DSN)
# ====================================================================
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
SENTRY_ENVIRONMENT = os.environ.get('SENTRY_ENVIRONMENT', 'development')
SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '1.0'))
SENTRY_PROFILES_SAMPLE_RATE = float(os.environ.get('SENTRY_PROFILES_SAMPLE_RATE', '0.1'))
SENTRY_SEND_DEFAULT_PII = os.environ.get('SENTRY_SEND_DEFAULT_PII', 'false').lower() == 'true'

# Validação e log de configuração Sentry
if SENTRY_DSN:
    print(f"✅ Sentry configurado para ambiente: {SENTRY_ENVIRONMENT}", file=sys.stderr)
    print(f"   Traces sample rate: {SENTRY_TRACES_SAMPLE_RATE}", file=sys.stderr)
else:
    print("⚠️  SENTRY_DSN não configurado - observabilidade desactivada", file=sys.stderr)


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
