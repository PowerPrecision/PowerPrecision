"""
Bulk AI Document Analysis Routes
Upload de documentos para análise com IA e preenchimento automático das fichas de clientes.

IMPORTANTE: Os ficheiros são processados um a um pelo frontend.
O endpoint /analyze-single recebe e processa um ficheiro de cada vez.
"""
import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from database import db
from models.auth import UserRole
from services.auth import require_roles, get_current_user
from services.ai_document import (
    MAX_FILE_SIZE,
    detect_document_type,
    get_mime_type,
    validate_file_size,
    analyze_single_document,
    build_update_data_from_extraction
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/bulk", tags=["AI Bulk Analysis"])

# Tamanho do chunk para leitura (64KB)
CHUNK_SIZE = 64 * 1024


class SingleAnalysisResult(BaseModel):
    success: bool
    client_name: str
    filename: str
    document_type: str = ""
    fields_extracted: List[str] = []
    updated: bool = False
    error: Optional[str] = None


async def find_client_by_name(client_name: str) -> Optional[dict]:
    """Encontrar cliente pelo nome (busca flexível)."""
    if not client_name:
        return None
    
    client_name = client_name.strip()
    
    # Busca exacta
    process = await db.processes.find_one(
        {"client_name": client_name},
        {"_id": 0}
    )
    if process:
        return process
    
    # Busca case-insensitive
    process = await db.processes.find_one(
        {"client_name": {"$regex": f"^{client_name}$", "$options": "i"}},
        {"_id": 0}
    )
    if process:
        return process
    
    # Busca parcial
    process = await db.processes.find_one(
        {"client_name": {"$regex": client_name, "$options": "i"}},
        {"_id": 0}
    )
    return process


async def read_file_with_limit(file: UploadFile) -> bytes:
    """
    Ler ficheiro com limite de tamanho.
    Lê em chunks para não sobrecarregar a memória.
    """
    chunks = []
    total_size = 0
    
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise ValueError(f"Ficheiro excede o limite de {MAX_FILE_SIZE // (1024*1024)}MB")
        
        chunks.append(chunk)
    
    return b''.join(chunks)


async def update_client_data(process_id: str, extracted_data: dict, document_type: str) -> bool:
    """Actualizar ficha do cliente com dados extraídos."""
    try:
        # Obter dados existentes
        process = await db.processes.find_one(
            {"id": process_id},
            {"_id": 0, "personal_data": 1, "financial_data": 1, "real_estate_data": 1}
        )
        
        # Construir dados de actualização
        update_data = build_update_data_from_extraction(
            extracted_data,
            document_type,
            process or {}
        )
        
        # Aplicar actualização
        if len(update_data) > 1:
            result = await db.processes.update_one(
                {"id": process_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao actualizar cliente {process_id}: {e}")
        return False


@router.post("/analyze-single", response_model=SingleAnalysisResult)
async def analyze_single_file(
    file: UploadFile = File(...),
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Analisar um único ficheiro.
    
    O frontend envia um ficheiro de cada vez, evitando problemas de memória
    e ficheiros fechados prematuramente pelo browser.
    
    O path do ficheiro deve ter o formato: NomeCliente/documento.pdf
    """
    filename = file.filename or "documento.pdf"
    
    # Extrair nome do cliente do path
    parts = filename.replace("\\", "/").split("/")
    
    if len(parts) >= 2:
        client_name = parts[-2]
        doc_filename = parts[-1]
    else:
        doc_filename = parts[0]
        if "_" in doc_filename:
            client_name = doc_filename.rsplit("_", 1)[0]
        else:
            client_name = "Desconhecido"
    
    result = SingleAnalysisResult(
        success=False,
        client_name=client_name,
        filename=doc_filename
    )
    
    try:
        # Ler ficheiro imediatamente (não deixar à espera)
        content = await read_file_with_limit(file)
        
        # Procurar cliente
        process = await find_client_by_name(client_name)
        if not process:
            result.error = f"Cliente não encontrado: {client_name}"
            return result
        
        process_id = process.get("id")
        
        # Detectar tipo de documento
        document_type = detect_document_type(doc_filename)
        result.document_type = document_type
        
        # Analisar com IA
        analysis_result = await analyze_single_document(
            content=content,
            filename=doc_filename,
            client_name=client_name,
            process_id=process_id
        )
        
        if analysis_result.get("success") and analysis_result.get("extracted_data"):
            result.success = True
            result.fields_extracted = list(analysis_result["extracted_data"].keys())
            
            # Actualizar ficha do cliente
            updated = await update_client_data(
                process_id,
                analysis_result["extracted_data"],
                document_type
            )
            result.updated = updated
            
            logger.info(f"Analisado {doc_filename} para {client_name}: {len(result.fields_extracted)} campos extraídos")
        else:
            result.error = analysis_result.get("error", "Erro na análise")
            logger.warning(f"Falha ao analisar {doc_filename}: {result.error}")
        
    except ValueError as e:
        result.error = str(e)
    except Exception as e:
        result.error = f"Erro inesperado: {str(e)}"
        logger.error(f"Erro ao processar {filename}: {e}")
    
    return result


@router.get("/clients-list")
async def get_clients_list(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Obter lista de clientes para referência no upload."""
    clients = await db.processes.find(
        {},
        {"_id": 0, "id": 1, "client_name": 1, "process_number": 1}
    ).sort("client_name", 1).to_list(None)
    
    return {
        "total": len(clients),
        "clients": [
            {
                "id": c.get("id"),
                "name": c.get("client_name"),
                "number": c.get("process_number")
            }
            for c in clients
        ]
    }
