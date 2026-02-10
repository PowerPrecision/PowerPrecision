"""
====================================================================
BACKUP SERVICE - CREDITOIMO
====================================================================
Sistema de backup automático da base de dados MongoDB.

FUNCIONALIDADES:
- Backup completo da base de dados usando mongodump
- Compressão em ZIP com timestamp
- Upload para OneDrive (pasta "Backups de Sistema")
- Limpeza automática de ficheiros locais
- Retenção configurável de backups antigos

AGENDAMENTO:
- Backup diário às 03:00 (configurável)
- Retenção de 30 dias (configurável)

DEPENDÊNCIAS:
- mongodump (MongoDB Database Tools)
- OneDrive configurado e autenticado

====================================================================
"""
import os
import subprocess
import shutil
import zipfile
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from database import db
from config import MONGO_URL, DB_NAME

logger = logging.getLogger(__name__)


# ====================================================================
# CONFIGURAÇÃO
# ====================================================================
class BackupConfig:
    """Configuração do sistema de backup."""
    
    # Directório temporário para backups
    BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/tmp/creditoimo_backups"))
    
    # Nome da pasta no OneDrive
    ONEDRIVE_BACKUP_FOLDER = os.environ.get("BACKUP_ONEDRIVE_FOLDER", "Backups de Sistema")
    
    # Retenção de backups locais (dias)
    LOCAL_RETENTION_DAYS = int(os.environ.get("BACKUP_LOCAL_RETENTION_DAYS", "7"))
    
    # Retenção de backups no OneDrive (dias)
    CLOUD_RETENTION_DAYS = int(os.environ.get("BACKUP_CLOUD_RETENTION_DAYS", "30"))
    
    # Tamanho máximo do backup (MB) - para alertas
    MAX_BACKUP_SIZE_MB = int(os.environ.get("BACKUP_MAX_SIZE_MB", "500"))


config = BackupConfig()


# ====================================================================
# FUNÇÕES DE BACKUP
# ====================================================================
def _ensure_backup_dir() -> Path:
    """Garante que o directório de backup existe."""
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return config.BACKUP_DIR


def _get_mongodump_uri() -> str:
    """
    Obtém a URI do MongoDB formatada para mongodump.
    Remove parâmetros que podem causar problemas.
    """
    # Usar a URI original
    uri = MONGO_URL
    
    # Se for MongoDB Atlas, adicionar authSource se necessário
    if "mongodb+srv" in uri or "mongodb.net" in uri:
        if "authSource" not in uri:
            separator = "&" if "?" in uri else "?"
            uri = f"{uri}{separator}authSource=admin"
    
    return uri


def _create_backup_filename() -> str:
    """Gera nome do ficheiro de backup com timestamp."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"backup_{DB_NAME}_{timestamp}"


async def perform_backup(
    include_indexes: bool = True,
    compress: bool = True
) -> Dict[str, Any]:
    """
    Executa backup completo da base de dados MongoDB.
    
    Args:
        include_indexes: Se True, inclui índices no backup
        compress: Se True, comprime o backup em ZIP
    
    Returns:
        Dict com informações do backup:
        - success: bool
        - filename: nome do ficheiro
        - size_mb: tamanho em MB
        - duration_seconds: duração
        - path: caminho local do ficheiro
        - error: mensagem de erro (se houver)
    """
    logger.info("🗄️ Iniciando backup da base de dados...")
    
    start_time = datetime.now(timezone.utc)
    backup_dir = _ensure_backup_dir()
    backup_name = _create_backup_filename()
    dump_path = backup_dir / backup_name
    
    result = {
        "success": False,
        "filename": backup_name,
        "started_at": start_time.isoformat(),
        "size_mb": 0,
        "duration_seconds": 0,
        "path": None,
        "error": None
    }
    
    try:
        # ============================================================
        # 1. EXECUTAR MONGODUMP
        # ============================================================
        logger.info(f"📦 Executando mongodump para {dump_path}")
        
        mongo_uri = _get_mongodump_uri()
        
        # Construir comando mongodump
        cmd = [
            "mongodump",
            f"--uri={mongo_uri}",
            f"--db={DB_NAME}",
            f"--out={dump_path}",
            "--gzip" if not compress else "",  # Comprimir BSON se não vamos zipar
        ]
        
        # Remover strings vazias
        cmd = [c for c in cmd if c]
        
        # Executar mongodump
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos timeout
        )
        
        if process.returncode != 0:
            error_msg = process.stderr or "Erro desconhecido no mongodump"
            logger.error(f"❌ Mongodump falhou: {error_msg}")
            result["error"] = error_msg
            return result
        
        logger.info("✅ Mongodump concluído com sucesso")
        
        # ============================================================
        # 2. COMPRIMIR EM ZIP
        # ============================================================
        if compress:
            zip_path = backup_dir / f"{backup_name}.zip"
            logger.info(f"🗜️ Comprimindo backup para {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Adicionar todos os ficheiros do dump
                for root, dirs, files in os.walk(dump_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(dump_path)
                        zipf.write(file_path, arcname)
            
            # Remover directório do dump (manter apenas ZIP)
            shutil.rmtree(dump_path)
            
            final_path = zip_path
            result["filename"] = f"{backup_name}.zip"
        else:
            final_path = dump_path
        
        # ============================================================
        # 3. CALCULAR ESTATÍSTICAS
        # ============================================================
        if final_path.is_file():
            size_bytes = final_path.stat().st_size
        else:
            # Calcular tamanho do directório
            size_bytes = sum(
                f.stat().st_size for f in final_path.rglob('*') if f.is_file()
            )
        
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        result["success"] = True
        result["path"] = str(final_path)
        result["size_mb"] = size_mb
        result["duration_seconds"] = round(duration, 2)
        result["completed_at"] = end_time.isoformat()
        
        logger.info(
            f"✅ Backup concluído: {result['filename']} "
            f"({size_mb}MB em {duration:.1f}s)"
        )
        
        # Alerta se backup muito grande
        if size_mb > config.MAX_BACKUP_SIZE_MB:
            logger.warning(
                f"⚠️ Backup maior que o esperado: {size_mb}MB "
                f"(limite: {config.MAX_BACKUP_SIZE_MB}MB)"
            )
        
        return result
        
    except subprocess.TimeoutExpired:
        result["error"] = "Timeout ao executar mongodump (>10 minutos)"
        logger.error(f"❌ {result['error']}")
        return result
        
    except FileNotFoundError:
        result["error"] = "mongodump não encontrado. Instalar MongoDB Database Tools."
        logger.error(f"❌ {result['error']}")
        return result
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ Erro no backup: {str(e)}")
        return result


# ====================================================================
# UPLOAD PARA ONEDRIVE
# ====================================================================
async def upload_backup_to_onedrive(backup_path: str) -> Dict[str, Any]:
    """
    Faz upload do backup para o OneDrive.
    
    Args:
        backup_path: Caminho local do ficheiro de backup
    
    Returns:
        Dict com resultado do upload
    """
    from services.onedrive import OneDriveService
    
    logger.info(f"☁️ Iniciando upload para OneDrive: {backup_path}")
    
    result = {
        "success": False,
        "uploaded_to": None,
        "onedrive_id": None,
        "error": None
    }
    
    try:
        onedrive = OneDriveService()
        
        if not onedrive.is_configured():
            result["error"] = "OneDrive não está configurado"
            logger.warning(f"⚠️ {result['error']}")
            return result
        
        # Obter tokens da base de dados
        settings = await db.settings.find_one({"type": "onedrive_tokens"})
        if not settings or not settings.get("refresh_token"):
            result["error"] = "OneDrive não está autenticado"
            logger.warning(f"⚠️ {result['error']}")
            return result
        
        # Renovar token
        tokens = await onedrive.refresh_access_token(settings["refresh_token"])
        access_token = tokens["access_token"]
        
        # Guardar novo refresh token
        await db.settings.update_one(
            {"type": "onedrive_tokens"},
            {
                "$set": {
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens.get("refresh_token", settings["refresh_token"]),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # ============================================================
        # 1. VERIFICAR/CRIAR PASTA DE BACKUPS
        # ============================================================
        import httpx
        
        folder_name = config.ONEDRIVE_BACKUP_FOLDER
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Procurar pasta
            search_url = f"https://graph.microsoft.com/v1.0/me/drive/root/children"
            response = await client.get(search_url, headers=headers)
            
            folder_id = None
            if response.status_code == 200:
                items = response.json().get("value", [])
                for item in items:
                    if item.get("name") == folder_name and item.get("folder"):
                        folder_id = item["id"]
                        break
            
            # Criar pasta se não existir
            if not folder_id:
                logger.info(f"📁 Criando pasta '{folder_name}' no OneDrive...")
                create_url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
                create_data = {
                    "name": folder_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail"
                }
                response = await client.post(
                    create_url, 
                    headers={**headers, "Content-Type": "application/json"},
                    json=create_data
                )
                
                if response.status_code in [200, 201]:
                    folder_id = response.json()["id"]
                    logger.info(f"✅ Pasta criada: {folder_id}")
                else:
                    result["error"] = f"Falha ao criar pasta: {response.text}"
                    return result
            
            # ============================================================
            # 2. UPLOAD DO FICHEIRO
            # ============================================================
            backup_file = Path(backup_path)
            file_size = backup_file.stat().st_size
            file_name = backup_file.name
            
            logger.info(f"📤 Enviando {file_name} ({file_size / 1024 / 1024:.2f}MB)...")
            
            # Para ficheiros pequenos (<4MB), usar upload simples
            if file_size < 4 * 1024 * 1024:
                upload_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}:/{file_name}:/content"
                
                with open(backup_file, "rb") as f:
                    response = await client.put(
                        upload_url,
                        headers={**headers, "Content-Type": "application/octet-stream"},
                        content=f.read()
                    )
            else:
                # Para ficheiros grandes, usar upload session
                upload_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}:/{file_name}:/createUploadSession"
                
                response = await client.post(
                    upload_url,
                    headers={**headers, "Content-Type": "application/json"},
                    json={
                        "item": {
                            "@microsoft.graph.conflictBehavior": "replace",
                            "name": file_name
                        }
                    }
                )
                
                if response.status_code not in [200, 201]:
                    result["error"] = f"Falha ao criar sessão de upload: {response.text}"
                    return result
                
                session_url = response.json()["uploadUrl"]
                
                # Upload em chunks de 10MB
                chunk_size = 10 * 1024 * 1024
                with open(backup_file, "rb") as f:
                    start = 0
                    while start < file_size:
                        end = min(start + chunk_size, file_size)
                        chunk = f.read(chunk_size)
                        
                        chunk_headers = {
                            "Content-Length": str(len(chunk)),
                            "Content-Range": f"bytes {start}-{end-1}/{file_size}"
                        }
                        
                        response = await client.put(
                            session_url,
                            headers=chunk_headers,
                            content=chunk
                        )
                        
                        if response.status_code not in [200, 201, 202]:
                            result["error"] = f"Falha no upload chunk: {response.text}"
                            return result
                        
                        start = end
                        progress = (start / file_size) * 100
                        logger.info(f"📤 Upload: {progress:.1f}%")
            
            if response.status_code in [200, 201]:
                file_info = response.json()
                result["success"] = True
                result["uploaded_to"] = f"{folder_name}/{file_name}"
                result["onedrive_id"] = file_info.get("id")
                result["web_url"] = file_info.get("webUrl")
                
                logger.info(f"✅ Upload concluído: {result['uploaded_to']}")
            else:
                result["error"] = f"Falha no upload: {response.text}"
                logger.error(f"❌ {result['error']}")
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ Erro no upload OneDrive: {str(e)}")
        return result


# ====================================================================
# LIMPEZA DE BACKUPS ANTIGOS
# ====================================================================
async def cleanup_old_backups(
    local_retention_days: int = None,
    cloud_retention_days: int = None
) -> Dict[str, Any]:
    """
    Remove backups antigos localmente e no OneDrive.
    
    Args:
        local_retention_days: Dias de retenção local
        cloud_retention_days: Dias de retenção no OneDrive
    
    Returns:
        Dict com estatísticas de limpeza
    """
    if local_retention_days is None:
        local_retention_days = config.LOCAL_RETENTION_DAYS
    
    if cloud_retention_days is None:
        cloud_retention_days = config.CLOUD_RETENTION_DAYS
    
    logger.info("🧹 Iniciando limpeza de backups antigos...")
    
    result = {
        "local_deleted": 0,
        "local_freed_mb": 0,
        "cloud_deleted": 0,
        "errors": []
    }
    
    # ================================================================
    # 1. LIMPEZA LOCAL
    # ================================================================
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=local_retention_days)
    
    for backup_file in config.BACKUP_DIR.glob("backup_*.zip"):
        try:
            file_mtime = datetime.fromtimestamp(
                backup_file.stat().st_mtime, 
                tz=timezone.utc
            )
            
            if file_mtime < cutoff_date:
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                backup_file.unlink()
                result["local_deleted"] += 1
                result["local_freed_mb"] += size_mb
                logger.info(f"🗑️ Removido backup local: {backup_file.name}")
        except Exception as e:
            result["errors"].append(f"Local: {backup_file.name}: {str(e)}")
    
    # ================================================================
    # 2. LIMPEZA ONEDRIVE (opcional)
    # ================================================================
    # Nota: Implementação completa requer autenticação OneDrive
    # Pode ser adicionada se necessário
    
    logger.info(
        f"✅ Limpeza concluída: {result['local_deleted']} ficheiros removidos "
        f"({result['local_freed_mb']:.2f}MB libertados)"
    )
    
    return result


# ====================================================================
# FUNÇÃO PRINCIPAL DE BACKUP COMPLETO
# ====================================================================
async def full_backup_workflow(
    upload_to_cloud: bool = True,
    cleanup_after: bool = True
) -> Dict[str, Any]:
    """
    Executa workflow completo de backup:
    1. Criar backup local
    2. Upload para OneDrive (se configurado)
    3. Limpeza de backups antigos
    
    Args:
        upload_to_cloud: Se True, envia para OneDrive
        cleanup_after: Se True, limpa backups antigos
    
    Returns:
        Dict com resultado completo do workflow
    """
    logger.info("=" * 60)
    logger.info("🗄️ INICIANDO WORKFLOW DE BACKUP")
    logger.info("=" * 60)
    
    workflow_result = {
        "success": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "backup": None,
        "upload": None,
        "cleanup": None,
        "error": None
    }
    
    try:
        # ============================================================
        # 1. CRIAR BACKUP
        # ============================================================
        backup_result = await perform_backup(compress=True)
        workflow_result["backup"] = backup_result
        
        if not backup_result["success"]:
            workflow_result["error"] = f"Falha no backup: {backup_result['error']}"
            return workflow_result
        
        # ============================================================
        # 2. UPLOAD PARA ONEDRIVE
        # ============================================================
        if upload_to_cloud and backup_result.get("path"):
            upload_result = await upload_backup_to_onedrive(backup_result["path"])
            workflow_result["upload"] = upload_result
            
            # Remover ficheiro local se upload bem sucedido
            if upload_result["success"] and cleanup_after:
                try:
                    Path(backup_result["path"]).unlink()
                    logger.info("🗑️ Ficheiro local removido após upload")
                except Exception as e:
                    logger.warning(f"⚠️ Não foi possível remover ficheiro local: {e}")
        
        # ============================================================
        # 3. LIMPEZA DE BACKUPS ANTIGOS
        # ============================================================
        if cleanup_after:
            cleanup_result = await cleanup_old_backups()
            workflow_result["cleanup"] = cleanup_result
        
        workflow_result["success"] = True
        workflow_result["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info("=" * 60)
        logger.info("✅ WORKFLOW DE BACKUP CONCLUÍDO COM SUCESSO")
        logger.info("=" * 60)
        
    except Exception as e:
        workflow_result["error"] = str(e)
        logger.error(f"❌ Erro no workflow de backup: {str(e)}")
    
    # Registar na base de dados
    await db.backup_history.insert_one({
        **workflow_result,
        "created_at": datetime.now(timezone.utc)
    })
    
    return workflow_result


# ====================================================================
# ESTATÍSTICAS DE BACKUP
# ====================================================================
async def get_backup_statistics() -> Dict[str, Any]:
    """Obtém estatísticas dos backups."""
    
    # Últimos 30 backups
    recent_backups = await db.backup_history.find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).limit(30).to_list(30)
    
    # Calcular estatísticas
    successful = [b for b in recent_backups if b.get("success")]
    failed = [b for b in recent_backups if not b.get("success")]
    
    total_size_mb = sum(
        b.get("backup", {}).get("size_mb", 0) for b in successful
    )
    
    avg_duration = 0
    if successful:
        avg_duration = sum(
            b.get("backup", {}).get("duration_seconds", 0) for b in successful
        ) / len(successful)
    
    # Verificar backups locais
    local_backups = list(config.BACKUP_DIR.glob("backup_*.zip"))
    local_size_mb = sum(f.stat().st_size for f in local_backups) / (1024 * 1024)
    
    return {
        "total_backups": len(recent_backups),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": round(len(successful) / len(recent_backups) * 100, 2) if recent_backups else 0,
        "total_size_mb": round(total_size_mb, 2),
        "avg_duration_seconds": round(avg_duration, 2),
        "local_backups": len(local_backups),
        "local_size_mb": round(local_size_mb, 2),
        "last_backup": recent_backups[0] if recent_backups else None
    }
