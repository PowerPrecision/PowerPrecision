"""
OneDrive Service - Acesso via Link Partilhado
Acede a ficheiros do OneDrive usando link de partilha público.
Não requer autenticação OAuth.
"""
import os
import base64
import logging
from typing import List, Optional, Dict
from thefuzz import fuzz, process as fuzzy_process
import httpx

logger = logging.getLogger(__name__)

# Configurações
ONEDRIVE_SHARED_LINK = os.environ.get('ONEDRIVE_SHARED_LINK', '')
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"


def encode_sharing_url(url: str) -> str:
    """
    Converter URL de partilha para token de acesso.
    Formato: u! + base64url(url)
    """
    # Codificar em base64
    encoded = base64.urlsafe_b64encode(url.encode()).decode()
    # Remover padding
    encoded = encoded.rstrip('=')
    # Adicionar prefixo
    return f"u!{encoded}"


class OneDriveSharedService:
    """
    Serviço de acesso ao OneDrive via link partilhado.
    """
    
    def __init__(self):
        self.shared_link = ONEDRIVE_SHARED_LINK
        self.share_token = encode_sharing_url(self.shared_link) if self.shared_link else None
        self._folders_cache = None
        self._cache_time = None
    
    def is_configured(self) -> bool:
        """Verifica se o link está configurado"""
        return bool(self.shared_link)
    
    async def list_client_folders(self, force_refresh: bool = False) -> List[Dict]:
        """
        Listar todas as pastas de clientes na pasta partilhada.
        Usa cache para evitar chamadas repetidas.
        """
        import time
        
        # Usar cache se disponível e recente (5 minutos)
        if not force_refresh and self._folders_cache and self._cache_time:
            if time.time() - self._cache_time < 300:
                return self._folders_cache
        
        if not self.share_token:
            logger.error("OneDrive: Link de partilha não configurado")
            return []
        
        url = f"{GRAPH_API_ENDPOINT}/shares/{self.share_token}/driveItem/children"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    params={"$top": 500}
                )
                
                if response.status_code == 401:
                    logger.error("OneDrive: Link de partilha expirado ou inválido")
                    return []
                
                if response.status_code != 200:
                    logger.error(f"OneDrive: Erro {response.status_code} - {response.text}")
                    return []
                
                data = response.json()
                folders = []
                
                for item in data.get("value", []):
                    if "folder" in item:
                        folders.append({
                            "id": item["id"],
                            "name": item["name"],
                            "web_url": item.get("webUrl"),
                            "child_count": item.get("folder", {}).get("childCount", 0),
                            "created": item.get("createdDateTime"),
                            "modified": item.get("lastModifiedDateTime")
                        })
                
                # Ordenar por nome
                folders.sort(key=lambda x: x["name"].lower())
                
                # Guardar cache
                self._folders_cache = folders
                self._cache_time = time.time()
                
                logger.info(f"OneDrive: Encontradas {len(folders)} pastas de clientes")
                return folders
                
        except httpx.TimeoutException:
            logger.error("OneDrive: Timeout ao listar pastas")
            return []
        except Exception as e:
            logger.error(f"OneDrive: Erro ao listar pastas: {e}")
            return []
    
    async def find_client_folder(
        self, 
        client_name: str,
        threshold: int = 65
    ) -> Optional[Dict]:
        """
        Encontrar pasta do cliente usando fuzzy matching.
        """
        folders = await self.list_client_folders()
        
        if not folders:
            return None
        
        folder_names = [f["name"] for f in folders]
        
        # Usar fuzzy matching
        best_match = fuzzy_process.extractOne(
            client_name,
            folder_names,
            scorer=fuzz.token_set_ratio
        )
        
        if best_match and best_match[1] >= threshold:
            matched_name = best_match[0]
            match_score = best_match[1]
            folder = next(f for f in folders if f["name"] == matched_name)
            
            logger.info(f"OneDrive: '{matched_name}' para '{client_name}' (score: {match_score}%)")
            
            return {
                **folder,
                "match_score": match_score,
                "searched_name": client_name
            }
        
        logger.warning(f"OneDrive: Sem correspondência para '{client_name}'")
        return None
    
    async def list_folder_files(self, folder_id: str) -> List[Dict]:
        """
        Listar ficheiros dentro de uma pasta.
        """
        if not self.share_token:
            return []
        
        # Obter o driveItem ID da pasta partilhada primeiro
        base_url = f"{GRAPH_API_ENDPOINT}/shares/{self.share_token}/driveItem"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Obter info da pasta partilhada
                base_response = await client.get(base_url)
                if base_response.status_code != 200:
                    logger.error(f"OneDrive: Erro ao obter pasta base: {base_response.text}")
                    return []
                
                base_data = base_response.json()
                drive_id = base_data.get("parentReference", {}).get("driveId")
                
                if not drive_id:
                    logger.error("OneDrive: Não foi possível obter driveId")
                    return []
                
                # Listar ficheiros da subpasta
                files_url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{folder_id}/children"
                
                response = await client.get(
                    files_url,
                    params={"$top": 200}
                )
                
                if response.status_code != 200:
                    logger.error(f"OneDrive: Erro ao listar ficheiros: {response.text}")
                    return []
                
                data = response.json()
                files = []
                
                for item in data.get("value", []):
                    is_folder = "folder" in item
                    
                    files.append({
                        "id": item["id"],
                        "name": item["name"],
                        "size": item.get("size", 0),
                        "is_folder": is_folder,
                        "mime_type": item.get("file", {}).get("mimeType") if not is_folder else None,
                        "created_at": item.get("createdDateTime"),
                        "modified_at": item.get("lastModifiedDateTime"),
                        "web_url": item.get("webUrl"),
                        "download_url": item.get("@microsoft.graph.downloadUrl")
                    })
                
                # Ordenar: pastas primeiro, depois por nome
                files.sort(key=lambda x: (not x["is_folder"], x["name"].lower()))
                
                return files
                
        except Exception as e:
            logger.error(f"OneDrive: Erro ao listar ficheiros: {e}")
            return []
    
    async def get_folder_web_url(self, folder_id: str) -> Optional[str]:
        """
        Obter URL web para abrir a pasta no browser.
        """
        if not self.share_token:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                base_response = await client.get(
                    f"{GRAPH_API_ENDPOINT}/shares/{self.share_token}/driveItem"
                )
                
                if base_response.status_code != 200:
                    return None
                
                base_data = base_response.json()
                drive_id = base_data.get("parentReference", {}).get("driveId")
                
                if not drive_id:
                    return None
                
                response = await client.get(
                    f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{folder_id}",
                    params={"$select": "webUrl"}
                )
                
                if response.status_code == 200:
                    return response.json().get("webUrl")
                
        except Exception as e:
            logger.error(f"OneDrive: Erro ao obter webUrl: {e}")
        
        return None


# Instância global
onedrive_shared_service = OneDriveSharedService()

if onedrive_shared_service.is_configured():
    logger.info("OneDrive: Link de partilha configurado ✓")
else:
    logger.warning("OneDrive: Link de partilha não configurado")
