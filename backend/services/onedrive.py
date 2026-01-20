import logging
from datetime import datetime, timezone, timedelta
from typing import List

import httpx
from fastapi import HTTPException

from config import ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET
from models.onedrive import OneDriveFile


logger = logging.getLogger(__name__)


class OneDriveService:
    def __init__(self):
        self.token = None
        self.token_expires = None
    
    async def get_access_token(self) -> str:
        """Get Microsoft Graph access token using client credentials"""
        if not all([ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET]):
            raise HTTPException(status_code=503, detail="OneDrive não configurado. Configure as variáveis ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID e ONEDRIVE_CLIENT_SECRET.")
        
        if self.token and self.token_expires and datetime.now(timezone.utc) < self.token_expires:
            return self.token
        
        token_url = f"https://login.microsoftonline.com/{ONEDRIVE_TENANT_ID}/oauth2/v2.0/token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data={
                "client_id": ONEDRIVE_CLIENT_ID,
                "client_secret": ONEDRIVE_CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            })
            
            if response.status_code != 200:
                logger.error(f"OneDrive auth failed: {response.text}")
                raise HTTPException(status_code=503, detail="Erro de autenticação OneDrive")
            
            data = response.json()
            self.token = data["access_token"]
            self.token_expires = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"] - 60)
            return self.token
    
    async def list_files(self, folder_path: str) -> List[OneDriveFile]:
        """List files in a OneDrive folder"""
        token = await self.get_access_token()
        
        encoded_path = folder_path.replace(" ", "%20")
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_path}:/children"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            
            if response.status_code == 404:
                return []
            
            if response.status_code != 200:
                logger.error(f"OneDrive list failed: {response.text}")
                raise HTTPException(status_code=503, detail="Erro ao listar ficheiros do OneDrive")
            
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
    
    async def get_download_url(self, item_id: str) -> str:
        """Get download URL for a file"""
        token = await self.get_access_token()
        
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Ficheiro não encontrado")
            
            data = response.json()
            return data.get("@microsoft.graph.downloadUrl", data.get("webUrl"))


onedrive_service = OneDriveService()
