"""
Bulk AI Document Analysis Routes
Upload múltiplo de documentos para análise com IA e preenchimento automático das fichas de clientes.
"""
import os
import io
import uuid
import base64
import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from database import db
from models.auth import UserRole
from services.auth import require_roles
from services.ai_document import (
    analyze_document_from_base64,
    map_cc_to_personal_data,
    map_recibo_to_financial_data,
    map_irs_to_financial_data
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/bulk", tags=["AI Bulk Analysis"])


class BulkAnalysisResult(BaseModel):
    success: bool
    total_files: int
    processed: int
    updated_clients: int
    errors: List[str] = []
    results: List[dict] = []


def detect_document_type(filename: str) -> str:
    """Detectar tipo de documento pelo nome do ficheiro."""
    filename_lower = filename.lower()
    
    if any(x in filename_lower for x in ['cc', 'cartao', 'cidadao', 'identificacao', 'bi']):
        return 'cc'
    elif any(x in filename_lower for x in ['recibo', 'vencimento', 'salario', 'ordenado']):
        return 'recibo_vencimento'
    elif any(x in filename_lower for x in ['irs', 'declaracao', 'imposto']):
        return 'irs'
    elif any(x in filename_lower for x in ['contrato', 'trabalho']):
        return 'contrato_trabalho'
    elif any(x in filename_lower for x in ['caderneta', 'predial', 'imovel']):
        return 'caderneta_predial'
    elif any(x in filename_lower for x in ['extrato', 'bancario', 'banco']):
        return 'extrato_bancario'
    else:
        return 'outro'


def get_mime_type(filename: str) -> str:
    """Obter MIME type pelo nome do ficheiro."""
    ext = filename.lower().split('.')[-1]
    mime_types = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
    }
    return mime_types.get(ext, 'application/octet-stream')


async def find_client_by_name(client_name: str) -> Optional[dict]:
    """Encontrar cliente pelo nome (busca flexível)."""
    if not client_name:
        return None
    
    # Limpar nome
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


async def update_client_with_extracted_data(process_id: str, extracted_data: dict, document_type: str) -> bool:
    """Actualizar ficha do cliente com dados extraídos."""
    try:
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        
        if document_type == 'cc':
            # Dados pessoais
            personal_update = {}
            if extracted_data.get('nif'):
                personal_update['nif'] = extracted_data['nif']
            if extracted_data.get('numero_documento'):
                personal_update['documento_id'] = extracted_data['numero_documento']
            if extracted_data.get('data_nascimento'):
                personal_update['data_nascimento'] = extracted_data['data_nascimento']
            if extracted_data.get('naturalidade'):
                personal_update['naturalidade'] = extracted_data['naturalidade']
            if extracted_data.get('nacionalidade'):
                personal_update['nacionalidade'] = extracted_data['nacionalidade']
            if extracted_data.get('sexo'):
                personal_update['sexo'] = extracted_data['sexo']
            if extracted_data.get('morada'):
                personal_update['morada'] = extracted_data['morada']
            if extracted_data.get('codigo_postal'):
                personal_update['codigo_postal'] = extracted_data['codigo_postal']
            
            if personal_update:
                # Merge com dados existentes
                process = await db.processes.find_one({"id": process_id}, {"_id": 0, "personal_data": 1})
                existing = process.get("personal_data", {}) if process else {}
                existing.update(personal_update)
                update_data["personal_data"] = existing
                
            # Actualizar email se extraído
            if extracted_data.get('email'):
                update_data["client_email"] = extracted_data['email']
                
        elif document_type in ['recibo_vencimento', 'irs']:
            # Dados financeiros
            financial_update = {}
            if extracted_data.get('salario_liquido'):
                financial_update['rendimento_mensal'] = extracted_data['salario_liquido']
            if extracted_data.get('salario_bruto'):
                financial_update['rendimento_bruto'] = extracted_data['salario_bruto']
            if extracted_data.get('empresa'):
                financial_update['empresa'] = extracted_data['empresa']
            if extracted_data.get('tipo_contrato'):
                financial_update['tipo_contrato'] = extracted_data['tipo_contrato']
            if extracted_data.get('categoria_profissional'):
                financial_update['categoria_profissional'] = extracted_data['categoria_profissional']
            if extracted_data.get('rendimento_liquido_anual'):
                financial_update['rendimento_anual'] = extracted_data['rendimento_liquido_anual']
                
            if financial_update:
                process = await db.processes.find_one({"id": process_id}, {"_id": 0, "financial_data": 1})
                existing = process.get("financial_data", {}) if process else {}
                existing.update(financial_update)
                update_data["financial_data"] = existing
                
        elif document_type == 'caderneta_predial':
            # Dados do imóvel
            real_estate_update = {}
            if extracted_data.get('artigo_matricial'):
                real_estate_update['artigo_matricial'] = extracted_data['artigo_matricial']
            if extracted_data.get('valor_patrimonial_tributario'):
                real_estate_update['valor_patrimonial'] = extracted_data['valor_patrimonial_tributario']
            if extracted_data.get('area_bruta'):
                real_estate_update['area'] = extracted_data['area_bruta']
            if extracted_data.get('localizacao'):
                real_estate_update['localizacao'] = extracted_data['localizacao']
                
            if real_estate_update:
                process = await db.processes.find_one({"id": process_id}, {"_id": 0, "real_estate_data": 1})
                existing = process.get("real_estate_data", {}) if process else {}
                existing.update(real_estate_update)
                update_data["real_estate_data"] = existing
        
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
    
    # Agrupar ficheiros por cliente
    clients_files = {}
    
    for file in files:
        # Extrair nome do cliente do path (pasta)
        # Formato esperado: "NomeCliente/ficheiro.pdf" ou "NomeCliente\ficheiro.pdf"
        filename = file.filename or ""
        parts = filename.replace("\\", "/").split("/")
        
        if len(parts) >= 2:
            client_name = parts[-2]  # Pasta pai
            doc_filename = parts[-1]  # Nome do ficheiro
        else:
            # Se não tiver pasta, tentar extrair do nome do ficheiro
            # Formato: "NomeCliente_CC.pdf"
            doc_filename = parts[0]
            if "_" in doc_filename:
                client_name = doc_filename.rsplit("_", 1)[0]
            else:
                client_name = "Desconhecido"
        
        if client_name not in clients_files:
            clients_files[client_name] = []
        clients_files[client_name].append((file, doc_filename))
    
    logger.info(f"Bulk analysis: {len(files)} ficheiros de {len(clients_files)} clientes")
    
    # Processar cada cliente
    for client_name, client_files in clients_files.items():
        # Encontrar cliente na base de dados
        process = await find_client_by_name(client_name)
        
        if not process:
            error_msg = f"Cliente não encontrado: {client_name}"
            result.errors.append(error_msg)
            logger.warning(error_msg)
            continue
        
        process_id = process.get("id")
        client_updated = False
        
        # Processar cada ficheiro do cliente
        for file, doc_filename in client_files:
            try:
                # Ler conteúdo do ficheiro
                content = await file.read()
                base64_content = base64.b64encode(content).decode('utf-8')
                
                # Detectar tipo de documento
                document_type = detect_document_type(doc_filename)
                mime_type = get_mime_type(doc_filename)
                
                logger.info(f"Analisando {doc_filename} ({document_type}) para {client_name}")
                
                # Analisar com IA
                analysis_result = await analyze_document_from_base64(
                    base64_content,
                    mime_type,
                    document_type
                )
                
                if analysis_result.get("success") and analysis_result.get("extracted_data"):
                    extracted_data = analysis_result["extracted_data"]
                    
                    # Actualizar ficha do cliente
                    updated = await update_client_with_extracted_data(
                        process_id,
                        extracted_data,
                        document_type
                    )
                    
                    if updated:
                        client_updated = True
                    
                    result.results.append({
                        "client_name": client_name,
                        "filename": doc_filename,
                        "document_type": document_type,
                        "success": True,
                        "fields_extracted": list(extracted_data.keys()),
                        "updated": updated
                    })
                    result.processed += 1
                    
                else:
                    error_msg = analysis_result.get("error", "Erro desconhecido")
                    result.results.append({
                        "client_name": client_name,
                        "filename": doc_filename,
                        "document_type": document_type,
                        "success": False,
                        "error": error_msg
                    })
                    result.errors.append(f"{client_name}/{doc_filename}: {error_msg}")
                    
            except Exception as e:
                error_msg = f"Erro ao processar {doc_filename}: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                result.results.append({
                    "client_name": client_name,
                    "filename": doc_filename,
                    "success": False,
                    "error": str(e)
                })
        
        if client_updated:
            result.updated_clients += 1
    
    result.success = result.processed > 0
    
    logger.info(f"Bulk analysis complete: {result.processed}/{result.total_files} processados, {result.updated_clients} clientes actualizados")
    
    return result


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
