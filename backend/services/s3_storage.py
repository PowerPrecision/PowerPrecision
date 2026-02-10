"""
S3 Storage Service - Alternativa Robusta ao OneDrive
Usa Amazon S3 (ou Cloudflare R2, MinIO, Google Cloud Storage)
"""
import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional, BinaryIO

logger = logging.getLogger(__name__)

# Configurações (Lê das variáveis de ambiente)
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-3') # Ex: eu-west-3 (Paris) ou us-east-1

class S3Service:
    def __init__(self):
        self.s3_client = None
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
        return self.s3_client is not None and bool(AWS_BUCKET_NAME)

    def upload_file(self, file_obj: BinaryIO, folder: str, filename: str, content_type: str = None) -> Optional[str]:
        """
        Faz upload de um ficheiro para uma 'pasta' específica.
        Retorna o URL público (se público) ou o caminho do ficheiro.
        """
        if not self.is_configured():
            return None

        # O 'Key' é o caminho completo: "pasta/cliente_x/ficheiro.pdf"
        # Removemos barras iniciais/finais para evitar erros
        clean_folder = folder.strip('/')
        object_name = f"{clean_folder}/{filename}"

        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        try:
            self.s3_client.upload_fileobj(
                file_obj,
                AWS_BUCKET_NAME,
                object_name,
                ExtraArgs=extra_args
            )
            logger.info(f"Upload S3 sucesso: {object_name}")
            return object_name
        except ClientError as e:
            logger.error(f"Erro no upload para S3: {e}")
            return None

    def list_files(self, folder: str) -> List[Dict]:
        """
        Lista ficheiros numa 'pasta'.
        """
        if not self.is_configured():
            return []

        clean_folder = folder.strip('/') + '/' # Garante que termina em / para listar conteúdo
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=AWS_BUCKET_NAME,
                Prefix=clean_folder
            )

            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Ignorar a própria pasta (se aparecer)
                    if obj['Key'] == clean_folder:
                        continue
                        
                    files.append({
                        "name": os.path.basename(obj['Key']),
                        "path": obj['Key'],
                        "size": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat(),
                        "type": "file"
                    })
            return files
        except ClientError as e:
            logger.error(f"Erro ao listar S3: {e}")
            return []

    def get_presigned_url(self, object_name: str, expiration=3600) -> Optional[str]:
        """
        Gera um link temporário (1 hora) para download/visualização segura.
        """
        if not self.is_configured():
            return None
            
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': AWS_BUCKET_NAME, 'Key': object_name},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Erro ao gerar link S3: {e}")
            return None

    def create_folder_structure(self, client_name: str):
        """
        Cria a estrutura de pastas padrão para um novo cliente.
        No S3, cria-se um ficheiro vazio '.keep' para marcar a pasta.
        """
        folders = ['Documentos Pessoais', 'Financeiros', 'Imóvel', 'Bancários']
        for f in folders:
            path = f"clientes/{client_name}/{f}/.keep"
            self.s3_client.put_object(Bucket=AWS_BUCKET_NAME, Key=path)

# Instância global
s3_service = S3Service()