import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

# Singleton para o cliente Motor
_client = None
_db = None


def get_motor_client():
    """Retorna o cliente Motor (criado on-demand)."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(mongo_url)
    return _client


def get_database():
    """Retorna a base de dados (criada on-demand)."""
    global _db
    if _db is None:
        _db = get_motor_client()[db_name]
    return _db


class DatabaseProxy:
    """
    Proxy para acesso à DB que cria a conexão on-demand.
    Permite usar `db.collection.find()` como antes.
    """
    def __getattr__(self, name):
        return getattr(get_database(), name)


# Manter compatibilidade com código existente: `from database import db`
db = DatabaseProxy()
