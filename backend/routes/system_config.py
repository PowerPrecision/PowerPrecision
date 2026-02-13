"""
Rotas para Configurações do Sistema
Permite ao admin configurar o sistema via interface
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from services.auth import get_current_user, require_roles
from models.auth import UserRole
from models.system_config import (
    SystemConfig, ConfigUpdateRequest, ConfigField,
    StorageProvider, EmailProvider, AIProvider
)
from services.system_config import (
    get_system_config, update_config_section, 
    mark_setup_completed, invalidate_config_cache
)

router = APIRouter(prefix="/system-config", tags=["System Configuration"])
logger = logging.getLogger(__name__)


# Definição dos campos de configuração para o frontend
CONFIG_FIELDS = {
    "storage": {
        "title": "Armazenamento de Ficheiros",
        "description": "Configurar o serviço para guardar documentos dos clientes",
        "fields": [
            ConfigField(
                key="provider",
                label="Serviço de Armazenamento",
                type="select",
                required=True,
                options=[
                    {"value": "none", "label": "Nenhum (Desactivado)"},
                    {"value": "aws_s3", "label": "Amazon S3 (Recomendado)"},
                    {"value": "onedrive", "label": "Microsoft OneDrive"},
                    {"value": "google_drive", "label": "Google Drive"},
                    {"value": "dropbox", "label": "Dropbox"},
                ],
                help_text="Escolha onde guardar os documentos dos clientes"
            ),
            # AWS S3
            ConfigField(
                key="aws_access_key_id",
                label="AWS Access Key ID",
                type="text",
                placeholder="AKIA...",
                depends_on={"provider": "aws_s3"},
                help_text="ID da chave de acesso AWS"
            ),
            ConfigField(
                key="aws_secret_access_key",
                label="AWS Secret Access Key",
                type="password",
                depends_on={"provider": "aws_s3"},
                help_text="Chave secreta AWS"
            ),
            ConfigField(
                key="aws_bucket_name",
                label="Nome do Bucket S3",
                type="text",
                placeholder="meu-bucket-documentos",
                depends_on={"provider": "aws_s3"},
                help_text="Nome do bucket S3 para documentos"
            ),
            ConfigField(
                key="aws_region",
                label="Região AWS",
                type="text",
                placeholder="eu-west-1",
                depends_on={"provider": "aws_s3"},
                help_text="Região do bucket S3 (ex: eu-west-1, us-east-1)"
            ),
            # OneDrive
            ConfigField(
                key="onedrive_client_id",
                label="Client ID (OneDrive)",
                type="text",
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                depends_on={"provider": "onedrive"},
                help_text="ID da aplicação Azure AD"
            ),
            ConfigField(
                key="onedrive_client_secret",
                label="Client Secret (OneDrive)",
                type="password",
                depends_on={"provider": "onedrive"},
                help_text="Segredo da aplicação Azure AD"
            ),
            ConfigField(
                key="onedrive_shared_url",
                label="URL da Pasta Partilhada (OneDrive)",
                type="text",
                placeholder="https://onedrive.live.com/?...",
                depends_on={"provider": "onedrive"},
                help_text="URL de partilha da pasta raiz dos clientes"
            ),
            # Google Drive
            ConfigField(
                key="google_client_id",
                label="Client ID (Google)",
                type="text",
                depends_on={"provider": "google_drive"},
                help_text="ID do cliente OAuth do Google Cloud"
            ),
            ConfigField(
                key="google_client_secret",
                label="Client Secret (Google)",
                type="password",
                depends_on={"provider": "google_drive"},
                help_text="Segredo do cliente OAuth"
            ),
            ConfigField(
                key="google_folder_id",
                label="ID da Pasta Raiz (Google Drive)",
                type="text",
                depends_on={"provider": "google_drive"},
                help_text="ID da pasta no Google Drive onde estão os clientes"
            ),
        ]
    },
    "email": {
        "title": "Configuração de Email",
        "description": "Configurar o servidor de email para envio e recepção",
        "fields": [
            ConfigField(
                key="provider",
                label="Tipo de Servidor",
                type="select",
                options=[
                    {"value": "none", "label": "Desactivado"},
                    {"value": "smtp", "label": "SMTP/IMAP Tradicional"},
                ],
            ),
            ConfigField(
                key="smtp_server",
                label="Servidor SMTP",
                type="text",
                placeholder="mail.exemplo.pt",
                depends_on={"provider": "smtp"},
            ),
            ConfigField(
                key="smtp_port",
                label="Porta SMTP",
                type="number",
                placeholder="465",
                depends_on={"provider": "smtp"},
            ),
            ConfigField(
                key="smtp_user",
                label="Utilizador SMTP",
                type="text",
                depends_on={"provider": "smtp"},
            ),
            ConfigField(
                key="smtp_password",
                label="Password SMTP",
                type="password",
                depends_on={"provider": "smtp"},
            ),
            ConfigField(
                key="imap_server",
                label="Servidor IMAP",
                type="text",
                placeholder="mail.exemplo.pt",
                depends_on={"provider": "smtp"},
            ),
            ConfigField(
                key="imap_port",
                label="Porta IMAP",
                type="number",
                placeholder="993",
                depends_on={"provider": "smtp"},
            ),
        ]
    },
    "ai": {
        "title": "Inteligência Artificial",
        "description": "Configurar o serviço de IA para análise de documentos",
        "fields": [
            ConfigField(
                key="provider",
                label="Fornecedor de IA",
                type="select",
                options=[
                    {"value": "emergent", "label": "Emergent (Recomendado)"},
                    {"value": "openai", "label": "OpenAI (Chave própria)"},
                ],
            ),
            ConfigField(
                key="api_key",
                label="Chave API",
                type="password",
                help_text="Chave da API do fornecedor escolhido",
            ),
            ConfigField(
                key="model",
                label="Modelo",
                type="select",
                options=[
                    {"value": "gpt-4o-mini", "label": "GPT-4o Mini (Rápido e económico)"},
                    {"value": "gpt-4o", "label": "GPT-4o (Mais preciso)"},
                ],
            ),
        ]
    },
    "trello": {
        "title": "Integração Trello",
        "description": "Sincronizar processos com um quadro Trello",
        "fields": [
            ConfigField(
                key="enabled",
                label="Activar Trello",
                type="boolean",
            ),
            ConfigField(
                key="api_key",
                label="API Key",
                type="text",
                depends_on={"enabled": True},
                help_text="Obter em https://trello.com/power-ups/admin"
            ),
            ConfigField(
                key="api_token",
                label="API Token",
                type="password",
                depends_on={"enabled": True},
            ),
            ConfigField(
                key="board_id",
                label="ID do Quadro",
                type="text",
                depends_on={"enabled": True},
                help_text="ID do quadro Trello a sincronizar"
            ),
        ]
    },
    "settings": {
        "title": "Definições Gerais",
        "description": "Personalizar a aparência e comportamento do sistema",
        "fields": [
            ConfigField(
                key="company_name",
                label="Nome da Empresa",
                type="text",
                required=True,
            ),
            ConfigField(
                key="company_subtitle",
                label="Subtítulo",
                type="text",
            ),
            ConfigField(
                key="primary_color",
                label="Cor Principal",
                type="text",
                placeholder="#0F766E",
                help_text="Código hexadecimal da cor"
            ),
            ConfigField(
                key="timezone",
                label="Fuso Horário",
                type="select",
                options=[
                    {"value": "Europe/Lisbon", "label": "Lisboa (Portugal)"},
                    {"value": "Europe/London", "label": "Londres (UK)"},
                    {"value": "Atlantic/Azores", "label": "Açores"},
                ],
            ),
            ConfigField(
                key="language",
                label="Idioma",
                type="select",
                options=[
                    {"value": "pt-PT", "label": "Português (Portugal)"},
                    {"value": "en-GB", "label": "English (UK)"},
                ],
            ),
        ]
    },
}


@router.get("")
async def get_config(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """
    Obter todas as configurações do sistema.
    Apenas admin pode aceder.
    """
    config = await get_system_config()
    
    # Mascarar passwords para segurança
    config_dict = config.model_dump()
    
    # Mascarar campos sensíveis
    sensitive_fields = [
        "onedrive_client_secret", "google_client_secret", 
        "dropbox_app_secret", "smtp_password", "imap_password",
        "api_key", "api_token", "dropbox_access_token"
    ]
    
    def mask_sensitive(obj, parent_key=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in sensitive_fields and value:
                    obj[key] = "••••••••" if value else None
                elif isinstance(value, dict):
                    mask_sensitive(value, key)
        return obj
    
    masked_config = mask_sensitive(config_dict)
    
    return {
        "config": masked_config,
        "fields": CONFIG_FIELDS,
    }


@router.get("/fields")
async def get_config_fields(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """
    Obter definição dos campos de configuração.
    Útil para o frontend construir os formulários.
    """
    return CONFIG_FIELDS


@router.patch("/{section}")
async def update_config(
    section: str,
    data: Dict[str, Any],
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Actualizar uma secção da configuração.
    """
    if section not in CONFIG_FIELDS:
        raise HTTPException(status_code=400, detail=f"Secção inválida: {section}")
    
    try:
        await update_config_section(section, data)
        logger.info(f"Configuração '{section}' actualizada por {user.get('email')}")
        
        return {
            "success": True,
            "message": f"Configuração '{section}' actualizada com sucesso",
            "section": section,
        }
    except Exception as e:
        logger.error(f"Erro ao actualizar configuração: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-connection/{service}")
async def test_service_connection(
    service: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Testar ligação a um serviço (email, storage, etc.).
    """
    config = await get_system_config()
    
    if service == "email":
        # Testar ligação SMTP
        try:
            import smtplib
            smtp = config.email
            if smtp.provider == "none":
                return {"success": False, "message": "Email não configurado"}
            
            # Verificar se as credenciais SMTP estão preenchidas
            if not smtp.smtp_server:
                return {"success": False, "message": "Servidor SMTP não configurado"}
            if not smtp.smtp_user:
                return {"success": False, "message": "Utilizador SMTP não configurado (preencha o campo 'Utilizador SMTP')"}
            if not smtp.smtp_password:
                return {"success": False, "message": "Password SMTP não configurada"}
            
            # Tentar conexão
            if smtp.smtp_use_ssl:
                server = smtplib.SMTP_SSL(smtp.smtp_server, smtp.smtp_port or 465, timeout=10)
            else:
                server = smtplib.SMTP(smtp.smtp_server, smtp.smtp_port or 587, timeout=10)
                server.starttls()
            
            server.login(smtp.smtp_user, smtp.smtp_password)
            server.quit()
            return {"success": True, "message": f"Ligação SMTP bem sucedida ({smtp.smtp_server})"}
        except smtplib.SMTPAuthenticationError:
            return {"success": False, "message": "Erro de autenticação: utilizador ou password incorrectos"}
        except smtplib.SMTPConnectError:
            return {"success": False, "message": "Não foi possível conectar ao servidor SMTP"}
        except TimeoutError:
            return {"success": False, "message": "Timeout: servidor SMTP não respondeu"}
        except Exception as e:
            return {"success": False, "message": f"Erro: {str(e)}"}
    
    elif service == "storage":
        storage = config.storage
        # Converter para string para comparação segura (enum ou string)
        provider_value = str(storage.provider.value) if hasattr(storage.provider, 'value') else str(storage.provider)
        
        if provider_value == "none":
            return {"success": False, "message": "Armazenamento não configurado"}
        elif provider_value == "aws_s3":
            # Testar ligação AWS S3
            try:
                from services.s3_storage import s3_service
                if s3_service.is_configured():
                    # Tentar verificar acesso ao bucket
                    try:
                        s3_service.s3_client.head_bucket(Bucket=s3_service.bucket_name)
                        return {"success": True, "message": f"AWS S3 conectado com sucesso! Bucket: {s3_service.bucket_name}"}
                    except s3_service.s3_client.exceptions.ClientError as e:
                        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                        if error_code == '403':
                            return {"success": False, "message": "Acesso negado ao bucket S3 - verifique as permissões"}
                        elif error_code == '404':
                            return {"success": False, "message": f"Bucket '{s3_service.bucket_name}' não encontrado"}
                        else:
                            return {"success": False, "message": f"Erro ao aceder bucket: {str(e)}"}
                    except Exception as e:
                        return {"success": False, "message": f"Erro ao aceder bucket: {str(e)}"}
                else:
                    # S3 não configurado via variáveis de ambiente, tentar com config da DB
                    if storage.aws_access_key_id and storage.aws_secret_access_key and storage.aws_bucket_name:
                        return {"success": True, "message": f"AWS S3 configurado via UI (Bucket: {storage.aws_bucket_name}). Configure as variáveis AWS no ambiente para activar."}
                    else:
                        return {"success": False, "message": "AWS S3 não está configurado. Preencha as credenciais ou configure as variáveis de ambiente."}
            except ImportError:
                return {"success": False, "message": "Módulo boto3 não instalado"}
            except Exception as e:
                return {"success": False, "message": f"Erro AWS S3: {str(e)}"}
        elif provider_value == "onedrive":
            # Verificar se tem as credenciais básicas
            if storage.onedrive_shared_url:
                return {"success": True, "message": "OneDrive configurado (via link partilhado)"}
            else:
                return {"success": False, "message": "URL de partilha não configurado"}
        elif provider_value == "google_drive":
            if storage.google_client_id and storage.google_folder_id:
                return {"success": True, "message": "Google Drive configurado"}
            else:
                return {"success": False, "message": "Credenciais do Google Drive em falta"}
        elif provider_value == "dropbox":
            if storage.dropbox_access_token:
                return {"success": True, "message": "Dropbox configurado"}
            else:
                return {"success": False, "message": "Token de acesso Dropbox não configurado"}
        elif provider_value == "local":
            return {"success": True, "message": "Armazenamento local activo"}
        
        return {"success": False, "message": f"Provider '{provider_value}' não suportado para teste"}
    
    elif service == "ai":
        ai = config.ai
        if not ai.api_key:
            return {"success": False, "message": "Chave API não configurada"}
        
        # Testar chamada simples
        try:
            from openai import OpenAI
            client = OpenAI(api_key=ai.api_key)
            response = client.chat.completions.create(
                model=ai.model,
                messages=[{"role": "user", "content": "Diz OK"}],
                max_tokens=5
            )
            return {"success": True, "message": "Ligação à IA bem sucedida"}
        except Exception as e:
            return {"success": False, "message": f"Erro: {str(e)}"}
    
    elif service == "trello":
        trello = config.trello
        if not trello.enabled:
            return {"success": False, "message": "Trello não activado"}
        
        try:
            import httpx
            url = f"https://api.trello.com/1/boards/{trello.board_id}?key={trello.api_key}&token={trello.api_token}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    board = response.json()
                    return {"success": True, "message": f"Ligado ao quadro: {board.get('name')}"}
                else:
                    return {"success": False, "message": f"Erro: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Erro: {str(e)}"}
    
    elif service == "mongodb" or service == "database":
        # Testar ligação MongoDB
        try:
            from database import db
            # Fazer uma query simples para testar a ligação
            result = await db.command("ping")
            if result.get("ok") == 1:
                # Obter estatísticas
                stats = await db.command("dbStats")
                collections = stats.get("collections", 0)
                return {"success": True, "message": f"MongoDB conectado. {collections} colecções."}
            else:
                return {"success": False, "message": "MongoDB não respondeu ao ping"}
        except Exception as e:
            return {"success": False, "message": f"Erro: {str(e)}"}
    
    return {"success": False, "message": "Serviço desconhecido"}


@router.post("/complete-setup")
async def complete_setup(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """
    Marcar a configuração inicial como concluída.
    """
    await mark_setup_completed()
    return {"success": True, "message": "Configuração inicial concluída"}


@router.get("/storage-info")
async def get_storage_info(user: dict = Depends(get_current_user)):
    """
    Obter informação sobre o sistema de armazenamento configurado.
    Disponível para todos os utilizadores autenticados.
    
    Retorna:
    - provider: Tipo de storage (aws_s3, google_drive, onedrive, dropbox, none)
    - provider_label: Nome amigável do provider
    - configured: Se está configurado correctamente
    - base_url: URL base para aceder aos ficheiros (se aplicável)
    """
    config = await get_system_config()
    storage = config.storage
    
    # Converter para string para comparação segura
    provider_value = str(storage.provider.value) if hasattr(storage.provider, 'value') else str(storage.provider)
    
    # Mapear provider para label amigável
    provider_labels = {
        "none": "Não configurado",
        "aws_s3": "Amazon S3",
        "google_drive": "Google Drive",
        "onedrive": "OneDrive",
        "dropbox": "Dropbox"
    }
    
    result = {
        "provider": provider_value,
        "provider_label": provider_labels.get(provider_value, provider_value),
        "configured": False,
        "base_url": None,
        "can_browse": False  # Se permite navegação de pastas
    }
    
    if provider_value == "none":
        return result
    
    elif provider_value == "aws_s3":
        from services.s3_storage import s3_service
        result["configured"] = s3_service.is_configured()
        result["can_browse"] = True  # S3 permite listar ficheiros
        if s3_service.is_configured():
            result["base_url"] = f"s3://{s3_service.bucket_name}"
    
    elif provider_value == "onedrive":
        result["configured"] = bool(storage.onedrive_shared_url)
        result["base_url"] = storage.onedrive_shared_url
        result["can_browse"] = False  # OneDrive usa links externos
    
    elif provider_value == "google_drive":
        result["configured"] = bool(storage.google_folder_id)
        if storage.google_folder_id:
            result["base_url"] = f"https://drive.google.com/drive/folders/{storage.google_folder_id}"
        result["can_browse"] = False
    
    elif provider_value == "dropbox":
        result["configured"] = bool(storage.dropbox_access_token)
        result["can_browse"] = False
    
    return result


@router.post("/reset-cache")
async def reset_cache(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """
    Forçar recarga das configurações do sistema.
    """
    invalidate_config_cache()
    return {"success": True, "message": "Cache de configurações limpo"}
