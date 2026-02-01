"""
OneDrive Service - Integração com Microsoft OneDrive

NOTA: A integração automática com OneDrive está desativada.
Os utilizadores podem adicionar links manuais do OneDrive nos processos.

Este serviço só será ativado quando as variáveis de ambiente
ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID e ONEDRIVE_CLIENT_SECRET
estiverem corretamente configuradas.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from models.onedrive import OneDriveFile

logger = logging.getLogger(__name__)

# Verificar se OneDrive está configurado
ONEDRIVE_CONFIGURED = False

try:
    from config import ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET
    ONEDRIVE_CONFIGURED = all([ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET])
except ImportError:
    ONEDRIVE_TENANT_ID = None
    ONEDRIVE_CLIENT_ID = None
    ONEDRIVE_CLIENT_SECRET = None


class OneDriveService:
    """
    Serviço de integração com OneDrive.
    
    A integração automática está desativada por padrão.
    Os utilizadores podem adicionar links manuais do OneDrive.
    """
    
    def __init__(self):
        self.token = None
        self.token_expires = None
        self.enabled = ONEDRIVE_CONFIGURED
    
    def is_configured(self) -> bool:
        """Verifica se o OneDrive está configurado"""
        return self.enabled
    
    async def get_access_token(self) -> Optional[str]:
        """Get Microsoft Graph access token using client credentials"""
        if not self.enabled:
            logger.debug("OneDrive não está configurado - usando links manuais")
            return None
        
        if self.token and self.token_expires and datetime.now(timezone.utc) < self.token_expires:
            return self.token
        
        try:
            import httpx
            token_url = f"https://login.microsoftonline.com/{ONEDRIVE_TENANT_ID}/oauth2/v2.0/token"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(token_url, data={
                    "client_id": ONEDRIVE_CLIENT_ID,
                    "client_secret": ONEDRIVE_CLIENT_SECRET,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials"
                })
                
                if response.status_code != 200:
                    logger.error(f"OneDrive auth failed: {response.text}")
                    return None
                
                data = response.json()
                self.token = data["access_token"]
                self.token_expires = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"] - 60)
                return self.token
                
        except Exception as e:
            logger.error(f"Erro ao obter token OneDrive: {e}")
            return None
    
    async def list_files(self, folder_path: str) -> List[OneDriveFile]:
        """List files in a OneDrive folder"""
        if not self.enabled:
            return []
        
        token = await self.get_access_token()
        if not token:
            return []
        
        try:
            import httpx
            encoded_path = folder_path.replace(" ", "%20")
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_path}:/children"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
                
                if response.status_code == 404:
                    return []
                
                if response.status_code != 200:
                    logger.error(f"OneDrive list failed: {response.text}")
                    return []
                
                data = response.json()
                files = []
                
                for item in data.get("value", []):
                    files.append(OneDriveFile(
                        id=item["id"],
                        name=item["name"],
                        size=item.get("size"),
                        is_folder="folder" in item,
                        modified_at=item.get("lastModifiedDateTime"),
                        web_url=item.get("webUrl"),
                        download_url=item.get("@microsoft.graph.downloadUrl")
                    ))
                
                return files
                
        except Exception as e:
            logger.error(f"Erro ao listar ficheiros OneDrive: {e}")
            return []
    
    async def get_download_url(self, item_id: str) -> Optional[str]:
        """Get download URL for a file"""
        if not self.enabled:
            return None
        
        token = await self.get_access_token()
        if not token:
            return None
        
        try:
            import httpx
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                return data.get("@microsoft.graph.downloadUrl", data.get("webUrl"))
                
        except Exception as e:
            logger.error(f"Erro ao obter URL de download: {e}")
            return None


# Instância global do serviço
onedrive_service = OneDriveService()

# Log do estado da configuração
if ONEDRIVE_CONFIGURED:
    logger.info("OneDrive: Integração automática ATIVADA")
else:
    logger.info("OneDrive: Integração automática DESATIVADA - usar links manuais")
