"""
S3 Storage Service - Alternativa Robusta ao OneDrive
Usa Amazon S3 (ou Cloudflare R2, MinIO, Google Cloud Storage)
"""
import os
import re
import logging
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional, BinaryIO

logger = logging.getLogger(__name__)

# Configurações (Lê das variáveis de ambiente)
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-3')

# Categorias de documentos padrão
DEFAULT_CATEGORIES = [
    "Documentos Pessoais",
    "Financeiros", 
    "Imóvel",
    "Bancários",
    "Outros"
]


def sanitize_folder_name(name: str) -> str:
    """Remove caracteres especiais do nome da pasta."""
    if not name:
        return "cliente"
    # Remove acentos e caracteres especiais
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name[:50] if name else "cliente"


class S3Service:
    def __init__(self):
        self.s3_client = None
        self.bucket_name = AWS_BUCKET_NAME
        if AWS_ACCESS_KEY and AWS_SECRET_KEY:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=AWS_ACCESS_KEY,
                    aws_secret_access_key=AWS_SECRET_KEY,
                    region_name=AWS_REGION
                )
                logger.info("S3 Service inicializado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao ligar ao S3: {e}")
        else:
            logger.warning("Credenciais S3 não encontradas. O serviço não funcionará.")

    def is_configured(self) -> bool:
        return self.s3_client is not None and bool(self.bucket_name)

    def _get_client_base_path(
        self, 
        client_id: str, 
        client_name: str,
        second_client_name: str = None
    ) -> str:
        """
        Gera o caminho base para um cliente.
        
        Se houver segundo titular, o nome da pasta incluirá ambos os nomes
        separados por " e " (ex: "João Silva e Maria Santos").
        
        Formato: clientes/{client_id}_{nome1_e_nome2}
        
        Args:
            client_id: ID do processo/cliente
            client_name: Nome do primeiro titular
            second_client_name: Nome do segundo titular (opcional)
        
        Returns:
            Caminho base no S3
        """
        safe_name = sanitize_folder_name(client_name)
        
        # Incluir segundo titular se existir
        if second_client_name and second_client_name.strip():
            safe_second_name = sanitize_folder_name(second_client_name)
            combined_name = f"{safe_name}_e_{safe_second_name}"
            # Limitar tamanho total para evitar paths muito longos
            if len(combined_name) > 80:
                combined_name = combined_name[:80]
            return f"clientes/{client_id}_{combined_name}"
        
        return f"clientes/{client_id}_{safe_name}"

    def upload_file(
        self, 
        file_obj: BinaryIO, 
        client_id: str,
        client_name: str,
        category: str, 
        filename: str, 
        content_type: str = None
    ) -> Optional[str]:
        """
        Faz upload de um ficheiro para a pasta do cliente numa categoria específica.
        
        Args:
            file_obj: Objeto de ficheiro
            client_id: ID do processo/cliente
            client_name: Nome do cliente
            category: Categoria (ex: "Financeiros", "Documentos Pessoais")
            filename: Nome do ficheiro
            content_type: MIME type do ficheiro
            
        Returns:
            Caminho S3 do ficheiro ou None se falhar
        """
        if not self.is_configured():
            logger.error("S3 não configurado")
            return None

        base_path = self._get_client_base_path(client_id, client_name)
        safe_category = sanitize_folder_name(category)
        object_name = f"{base_path}/{safe_category}/{filename}"

        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_name,
                ExtraArgs=extra_args if extra_args else None
            )
            logger.info(f"Upload S3 sucesso: {object_name}")
            return object_name
        except ClientError as e:
            logger.error(f"Erro no upload para S3: {e}")
            return None

    def list_files(self, client_id: str, client_name: str) -> Dict[str, List[Dict]]:
        """
        Lista todos os ficheiros de um cliente organizados por categoria.
        
        Returns:
            Dict com categorias como chaves e listas de ficheiros como valores
        """
        if not self.is_configured():
            return {"error": "S3 não configurado", "files": {}}

        base_path = self._get_client_base_path(client_id, client_name)
        prefix = f"{base_path}/"
        
        try:
            # Usar paginator para lidar com muitos ficheiros
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            # Organizar por categoria
            files_by_category = {cat: [] for cat in DEFAULT_CATEGORIES}
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    key = obj['Key']
                    
                    # Ignorar ficheiros .keep (marcadores de pasta)
                    if key.endswith('.keep'):
                        continue
                    
                    # Extrair categoria do path
                    # Formato: clientes/{id}_{name}/{categoria}/{ficheiro}
                    parts = key.replace(prefix, '').split('/')
                    if len(parts) < 2:
                        continue
                    
                    category = parts[0].replace('_', ' ')
                    filename = parts[-1]
                    
                    # Encontrar categoria correspondente
                    matched_category = "Outros"
                    for cat in DEFAULT_CATEGORIES:
                        if cat.lower().replace(' ', '_') == category.lower().replace(' ', '_'):
                            matched_category = cat
                            break
                    
                    file_info = {
                        "name": filename,
                        "path": key,
                        "size": obj['Size'],
                        "size_formatted": self._format_size(obj['Size']),
                        "last_modified": obj['LastModified'].isoformat(),
                        "category": matched_category
                    }
                    
                    if matched_category in files_by_category:
                        files_by_category[matched_category].append(file_info)
                    else:
                        files_by_category["Outros"].append(file_info)
            
            # Calcular estatísticas
            total_files = sum(len(files) for files in files_by_category.values())
            total_size = sum(
                f['size'] 
                for files in files_by_category.values() 
                for f in files
            )
            
            return {
                "files": files_by_category,
                "categories": DEFAULT_CATEGORIES,
                "stats": {
                    "total_files": total_files,
                    "total_size": total_size,
                    "total_size_formatted": self._format_size(total_size)
                }
            }
            
        except ClientError as e:
            logger.error(f"Erro ao listar S3: {e}")
            return {"error": str(e), "files": {}}

    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para formato legível."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def get_presigned_url(self, object_name: str, expiration: int = 3600) -> Optional[str]:
        """
        Gera um link temporário (1 hora por defeito) para download/visualização.
        
        Args:
            object_name: Caminho S3 do ficheiro
            expiration: Tempo de validade em segundos
            
        Returns:
            URL pré-assinado ou None se falhar
        """
        if not self.is_configured():
            return None
            
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Erro ao gerar link S3: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """
        Elimina um ficheiro do S3.
        
        Args:
            object_name: Caminho S3 do ficheiro
            
        Returns:
            True se eliminado com sucesso
        """
        if not self.is_configured():
            return False
            
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"Ficheiro eliminado: {object_name}")
            return True
        except ClientError as e:
            logger.error(f"Erro ao eliminar ficheiro S3: {e}")
            return False

    def initialize_client_folders(self, client_id: str, client_name: str) -> bool:
        """
        Cria a estrutura de pastas padrão para um novo cliente.
        No S3, cria-se um ficheiro vazio '.keep' para marcar a pasta.
        
        Args:
            client_id: ID do processo/cliente
            client_name: Nome do cliente
            
        Returns:
            True se criado com sucesso
        """
        if not self.is_configured():
            return False
            
        base_path = self._get_client_base_path(client_id, client_name)
        
        try:
            for category in DEFAULT_CATEGORIES:
                safe_category = sanitize_folder_name(category)
                path = f"{base_path}/{safe_category}/.keep"
                self.s3_client.put_object(
                    Bucket=self.bucket_name, 
                    Key=path,
                    Body=b''
                )
            logger.info(f"Estrutura de pastas criada para cliente: {client_id}")
            return True
        except ClientError as e:
            logger.error(f"Erro ao criar pastas S3: {e}")
            return False


# Instância global
s3_service = S3Service()