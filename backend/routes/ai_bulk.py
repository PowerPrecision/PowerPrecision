"""
Bulk AI Document Analysis Routes
Upload múltiplo de documentos para análise com IA e preenchimento automático das fichas de clientes.

NOTA: A lógica de negócio está em services/ai_document.py
Esta rota apenas recebe pedidos e devolve respostas.
"""
import os
import uuid
import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from database import db
from models.auth import UserRole
from services.auth import require_roles
from services.ai_document import (
    MAX_FILE_SIZE,
    MAX_CONCURRENT_ANALYSIS,
    detect_document_type,
    get_mime_type,
    validate_file_size,
    analyze_single_document,
    process_bulk_documents,
    build_update_data_from_extraction
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/bulk", tags=["AI Bulk Analysis"])

# Tamanho do chunk para leitura de ficheiros (64KB)
CHUNK_SIZE = 64 * 1024


class BulkAnalysisResult(BaseModel):
    success: bool
    total_files: int
    processed: int
    updated_clients: int
    errors: List[str] = []
    results: List[dict] = []


async def find_client_by_name(client_name: str) -> Optional[dict]:
    """Encontrar cliente pelo nome (busca flexível)."""
    if not client_name:
        return None
    
    client_name = client_name.strip()
    
    # Busca exacta primeiro
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
    
    # Busca parcial (contém o nome)
    process = await db.processes.find_one(
        {"client_name": {"$regex": client_name, "$options": "i"}},
        {"_id": 0}
    )
    return process


async def read_file_in_chunks(file: UploadFile) -> bytes:
    """
    Ler ficheiro em chunks para evitar problemas de memória.
    Valida o tamanho durante a leitura.
    """
    chunks = []
    total_size = 0
    
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        
        total_size += len(chunk)
        
        # Validar tamanho durante leitura
        if total_size > MAX_FILE_SIZE:
            raise ValueError(f"Ficheiro excede o limite de {MAX_FILE_SIZE / (1024*1024):.0f}MB")
        
        chunks.append(chunk)
    
    return b''.join(chunks)


async def update_client_with_extracted_data(
    process_id: str,
    extracted_data: dict,
    document_type: str
) -> bool:
    """Actualizar ficha do cliente com dados extraídos."""
    try:
        # Obter dados existentes
        process = await db.processes.find_one(
            {"id": process_id},
            {"_id": 0, "personal_data": 1, "financial_data": 1, "real_estate_data": 1}
        )
        
        # Construir dados de actualização usando função do serviço
        update_data = build_update_data_from_extraction(
            extracted_data,
            document_type,
            process or {}
        )
        
        # Aplicar actualização
        if len(update_data) > 1:  # Mais do que só updated_at
            result = await db.processes.update_one(
                {"id": process_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao actualizar cliente {process_id}: {e}")
        return False


@router.post("/analyze", response_model=BulkAnalysisResult)
async def bulk_analyze_documents(
    files: List[UploadFile] = File(...),
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Análise em lote de documentos.
    
    Estrutura esperada dos ficheiros:
    - NomeCliente/documento.pdf
    - NomeCliente/CC.pdf
    - NomeCliente/Recibo.pdf
    
    A IA analisa cada documento e preenche automaticamente a ficha do cliente correspondente.
    Apenas disponível para administradores.
    """
    result = BulkAnalysisResult(
        success=True,
        total_files=len(files),
        processed=0,
        updated_clients=0,
        errors=[],
        results=[]
    )
    
    # Fase 1: Agrupar ficheiros por cliente e preparar dados
    clients_data = {}  # client_name -> {process_id, files: [(content, filename)]}
    
    for file in files:
        filename = file.filename or ""
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
        
        # Ler ficheiro em chunks (com validação de tamanho)
        try:
            content = await read_file_in_chunks(file)
        except ValueError as e:
            result.errors.append(f"{client_name}/{doc_filename}: {str(e)}")
            continue
        except Exception as e:
            result.errors.append(f"{client_name}/{doc_filename}: Erro ao ler ficheiro - {str(e)}")
            continue
        
        if client_name not in clients_data:
            # Procurar cliente na BD
            process = await find_client_by_name(client_name)
            if not process:
                result.errors.append(f"Cliente não encontrado: {client_name}")
                continue
            
            clients_data[client_name] = {
                "process_id": process.get("id"),
                "files": []
            }
        
        clients_data[client_name]["files"].append({
            "content": content,
            "filename": doc_filename
        })
    
    logger.info(f"Bulk analysis: {len(files)} ficheiros de {len(clients_data)} clientes")
    
    # Fase 2: Preparar lista de ficheiros para processamento paralelo
    files_to_process = []
    for client_name, data in clients_data.items():
        for file_info in data["files"]:
            files_to_process.append({
                "content": file_info["content"],
                "filename": file_info["filename"],
                "client_name": client_name,
                "process_id": data["process_id"]
            })
    
    # Fase 3: Processar todos em paralelo usando o serviço
    if files_to_process:
        bulk_result = await process_bulk_documents(files_to_process)
        
        # Fase 4: Actualizar fichas dos clientes com resultados
        updated_clients = set()
        
        for r in bulk_result.get("results", []):
            result.results.append(r)
            
            if r.get("success") and r.get("extracted_data"):
                # Actualizar ficha do cliente
                updated = await update_client_with_extracted_data(
                    r["process_id"],
                    r["extracted_data"],
                    r["document_type"]
                )
                r["updated"] = updated
                
                if updated:
                    updated_clients.add(r["process_id"])
        
        result.processed = bulk_result.get("processed", 0)
        result.updated_clients = len(updated_clients)
        result.errors.extend(bulk_result.get("errors", []))
    
    result.success = result.processed > 0
    
    logger.info(
        f"Bulk analysis complete: {result.processed}/{result.total_files} processados, "
        f"{result.updated_clients} clientes actualizados"
    )
    
    return result


@router.post("/analyze-stream")
async def bulk_analyze_documents_stream(
    files: List[UploadFile] = File(...),
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Análise em lote com streaming de progresso.
    Retorna Server-Sent Events (SSE) com o progresso de cada ficheiro.
    """
    
    async def generate_progress():
        total_files = len(files)
        processed = 0
        errors = []
        results = []
        updated_clients = set()
        
        # Enviar início
        yield f"data: {json.dumps({'type': 'start', 'total': total_files})}\n\n"
        
        # Agrupar ficheiros por cliente
        clients_data = {}
        
        for file in files:
            filename = file.filename or ""
            parts = filename.replace("\\", "/").split("/")
            
            if len(parts) >= 2:
                client_name = parts[-2]
                doc_filename = parts[-1]
            else:
                doc_filename = parts[0]
                client_name = doc_filename.rsplit("_", 1)[0] if "_" in doc_filename else "Desconhecido"
            
            try:
                content = await read_file_in_chunks(file)
            except Exception as e:
                error_msg = f"{client_name}/{doc_filename}: {str(e)}"
                errors.append(error_msg)
                yield f"data: {json.dumps({'type': 'error', 'file': doc_filename, 'client': client_name, 'error': str(e)})}\n\n"
                continue
            
            if client_name not in clients_data:
                process = await find_client_by_name(client_name)
                if not process:
                    error_msg = f"Cliente não encontrado: {client_name}"
                    errors.append(error_msg)
                    yield f"data: {json.dumps({'type': 'error', 'file': doc_filename, 'client': client_name, 'error': 'Cliente não encontrado'})}\n\n"
                    continue
                
                clients_data[client_name] = {"process_id": process.get("id"), "files": []}
            
            clients_data[client_name]["files"].append({"content": content, "filename": doc_filename})
        
        # Processar cada ficheiro e enviar progresso
        for client_name, data in clients_data.items():
            for file_info in data["files"]:
                filename = file_info["filename"]
                
                # Enviar início de processamento
                yield f"data: {json.dumps({'type': 'processing', 'file': filename, 'client': client_name})}\n\n"
                
                # Analisar documento
                result = await analyze_single_document(
                    content=file_info["content"],
                    filename=filename,
                    client_name=client_name,
                    process_id=data["process_id"]
                )
                
                if result.get("success"):
                    # Actualizar ficha do cliente
                    updated = await update_client_with_extracted_data(
                        data["process_id"],
                        result["extracted_data"],
                        result["document_type"]
                    )
                    result["updated"] = updated
                    
                    if updated:
                        updated_clients.add(data["process_id"])
                    
                    processed += 1
                    
                    yield f"data: {json.dumps({'type': 'success', 'file': filename, 'client': client_name, 'fields': result.get('fields_extracted', []), 'updated': updated})}\n\n"
                else:
                    errors.append(f"{client_name}/{filename}: {result.get('error', 'Erro desconhecido')}")
                    yield f"data: {json.dumps({'type': 'error', 'file': filename, 'client': client_name, 'error': result.get('error', 'Erro desconhecido')})}\n\n"
                
                results.append(result)
        
        # Enviar resumo final
        yield f"data: {json.dumps({'type': 'complete', 'total': total_files, 'processed': processed, 'updated_clients': len(updated_clients), 'errors_count': len(errors)})}\n\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/clients-list")
async def get_clients_list(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Obter lista de clientes para referência no upload massivo."""
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
