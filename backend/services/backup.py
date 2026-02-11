import os
import logging
import shutil
import asyncio
import tempfile
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, DB_NAME

logger = logging.getLogger(__name__)


class BackupConfig:
    """Configuração do sistema de backup."""
    BACKUP_DIR = Path(tempfile.gettempdir()) / "creditoimo_backups"
    ONEDRIVE_BACKUP_FOLDER = os.environ.get("ONEDRIVE_BACKUP_FOLDER", "Backups")
    LOCAL_RETENTION_DAYS = int(os.environ.get("BACKUP_LOCAL_RETENTION_DAYS", "7"))
    CLOUD_RETENTION_DAYS = int(os.environ.get("BACKUP_CLOUD_RETENTION_DAYS", "30"))
    MAX_BACKUP_SIZE_MB = int(os.environ.get("BACKUP_MAX_SIZE_MB", "500"))


config = BackupConfig()


class BackupService:
    BACKUP_DIR = config.BACKUP_DIR

    def __init__(self):
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    async def create_backup(self):
        """Cria um backup completo da base de dados em JSON."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = self.BACKUP_DIR / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        logger.info(f"Iniciando backup em: {backup_path}")
        
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        try:
            collections = await db.list_collection_names()
            count = 0
            
            for col_name in collections:
                cursor = db[col_name].find({})
                docs = await cursor.to_list(length=None)
                
                from bson import json_util
                
                file_path = backup_path / f"{col_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(json_util.dumps(docs, indent=2))
                
                count += len(docs)
            
            shutil.make_archive(str(backup_path), 'zip', backup_path)
            zip_path = str(backup_path) + ".zip"
            
            shutil.rmtree(backup_path)
            
            logger.info(f"Backup concluído: {zip_path} ({count} documentos)")
            return zip_path
            
        except Exception as e:
            logger.error(f"Erro no backup: {e}")
            return None
        finally:
            client.close()


backup_service = BackupService()


async def get_backup_statistics() -> dict:
    """
    Obtém estatísticas dos backups.
    
    Returns:
        Dict com estatísticas de backups
    """
    from database import db
    
    stats = {
        "total_backups": 0,
        "successful_backups": 0,
        "success_rate": 0,
        "total_size_bytes": 0,
        "last_backup": None
    }
    
    # Contar backups no histórico
    history = await db.backup_history.find({}).sort("started_at", -1).limit(100).to_list(100)
    
    stats["total_backups"] = len(history)
    stats["successful_backups"] = len([h for h in history if h.get("status") == "completed"])
    
    if stats["total_backups"] > 0:
        stats["success_rate"] = (stats["successful_backups"] / stats["total_backups"]) * 100
        stats["last_backup"] = {
            "started_at": history[0].get("started_at"),
            "status": history[0].get("status"),
            "success": history[0].get("status") == "completed"
        }
    
    # Calcular tamanho dos ficheiros locais
    if config.BACKUP_DIR.exists():
        for backup_file in config.BACKUP_DIR.glob("backup_*.zip"):
            stats["total_size_bytes"] += backup_file.stat().st_size
    
    return stats


async def full_backup_workflow(upload_to_cloud: bool = True, cleanup_after: bool = True) -> dict:
    """
    Executa o workflow completo de backup.
    
    1. Cria backup local
    2. (Opcional) Upload para cloud
    3. (Opcional) Limpa backups antigos
    
    Returns:
        Dict com resultado do backup
    """
    result = {
        "success": False,
        "backup_path": None,
        "size_bytes": 0,
        "uploaded": False,
        "cleaned_up": False,
        "error": None
    }
    
    try:
        # 1. Criar backup
        zip_path = await backup_service.create_backup()
        
        if not zip_path:
            result["error"] = "Falha ao criar backup"
            return result
        
        result["backup_path"] = zip_path
        result["size_bytes"] = Path(zip_path).stat().st_size
        result["success"] = True
        
        # 2. Upload para cloud (implementar conforme necessário)
        if upload_to_cloud:
            # TODO: Implementar upload para OneDrive/S3
            result["uploaded"] = False  # Por agora não está implementado
        
        # 3. Limpar backups antigos
        if cleanup_after:
            cutoff = datetime.now() - timedelta(days=config.LOCAL_RETENTION_DAYS)
            for old_backup in config.BACKUP_DIR.glob("backup_*.zip"):
                try:
                    mtime = datetime.fromtimestamp(old_backup.stat().st_mtime)
                    if mtime < cutoff:
                        old_backup.unlink()
                        result["cleaned_up"] = True
                except Exception:
                    continue
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Erro no workflow de backup: {e}")
        return result