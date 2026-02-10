import os
import logging
import shutil
import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, DB_NAME

logger = logging.getLogger(__name__)

class BackupService:
    # CORREÇÃO DE SEGURANÇA: Usar tempfile.gettempdir()
    # Cria caminho seguro independente do sistema operativo e evita hardcoded /tmp
    BACKUP_DIR = Path(tempfile.gettempdir()) / "creditoimo_backups"

    def __init__(self):
        # Garantir que a diretoria existe
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    async def create_backup(self):
        """Cria um backup completo da base de dados em JSON."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = self.BACKUP_DIR / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        logger.info(f"Iniciando backup em: {backup_path}")
        
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DB_NAME]
        
        try:
            collections = await db.list_collection_names()
            count = 0
            
            for col_name in collections:
                cursor = db[col_name].find({})
                docs = await cursor.to_list(length=None)
                
                # Converter ObjectId e Datetime para string (JSON serializable simples)
                from bson import json_util
                
                file_path = backup_path / f"{col_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(json_util.dumps(docs, indent=2))
                
                count += len(docs)
            
            # Criar ZIP
            shutil.make_archive(str(backup_path), 'zip', backup_path)
            zip_path = str(backup_path) + ".zip"
            
            # Limpar pasta temporária json
            shutil.rmtree(backup_path)
            
            logger.info(f"Backup concluído: {zip_path} ({count} documentos)")
            return zip_path
            
        except Exception as e:
            logger.error(f"Erro no backup: {e}")
            return None
        finally:
            client.close()

backup_service = BackupService()