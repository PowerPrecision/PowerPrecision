"""
Bulk AI Document Analysis Routes
Upload de documentos para análise com IA e preenchimento automático das fichas de clientes.

IMPORTANTE: Os ficheiros são processados um a um pelo frontend.
O endpoint /analyze-single recebe e processa um ficheiro de cada vez.

FUNCIONALIDADES:
- Normalização de nomes de ficheiros
- Junção de CC frente+verso num único PDF para análise
- Conversão de PDFs scan para imagem
"""
import os
import re
import uuid
import base64
import logging
from typing import List, Optional, Dict, Tuple
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
    build_update_data_from_extraction,
    merge_images_to_pdf,
    analyze_document_from_base64
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/bulk", tags=["AI Bulk Analysis"])

# Tamanho do chunk para leitura (64KB)
CHUNK_SIZE = 64 * 1024

# Nomes normalizados de documentos
NORMALIZED_NAMES = {
    "cc": "CC.pdf",
    "recibo_vencimento": "Recibo_Vencimento.pdf",
    "irs": "IRS.pdf",
    "contrato_trabalho": "Contrato_Trabalho.pdf",
    "caderneta_predial": "Caderneta_Predial.pdf",
    "extrato_bancario": "Extrato_Bancario.pdf",
    "outro": "Documento.pdf"
}

# Cache temporário para CC frente/verso por cliente
# Estrutura: {process_id: {"frente": (bytes, mime), "verso": (bytes, mime)}}
cc_cache: Dict[str, Dict[str, Tuple[bytes, str]]] = {}


def is_cc_frente_or_verso(filename: str) -> Optional[str]:
    """
    Verificar se o ficheiro é frente ou verso do CC.
    
    Returns:
        "frente", "verso" ou None
    """
    filename_lower = filename.lower()
    
    # Padrões para frente
    frente_patterns = ["frente", "front", "_f.", "_f_", "cc_1", "cc1", "ccf"]
    for p in frente_patterns:
        if p in filename_lower:
            return "frente"
    
    # Padrões para verso
    verso_patterns = ["verso", "back", "tras", "_v.", "_v_", "cc_2", "cc2", "ccv"]
    for p in verso_patterns:
        if p in filename_lower:
            return "verso"
    
    return None


def get_normalized_filename(document_type: str) -> str:
    """Obter nome normalizado para o tipo de documento."""
    return NORMALIZED_NAMES.get(document_type, NORMALIZED_NAMES["outro"])


class SingleAnalysisResult(BaseModel):
    success: bool
    client_name: str
    filename: str
    document_type: str = ""
    fields_extracted: List[str] = []
    updated: bool = False
    error: Optional[str] = None


async def find_client_by_name(client_name: str) -> Optional[dict]:
    """
    Encontrar cliente pelo nome (busca flexível).
    Suporta nomes compostos como:
    - "João e Maria"
    - "João (Maria)"
    - "João / Maria"
    """
    if not client_name:
        return None
    
    client_name = client_name.strip()
    
    # 1. Busca exacta
    process = await db.processes.find_one(
        {"client_name": client_name},
        {"_id": 0}
    )
    if process:
        return process
    
    # 2. Busca case-insensitive exacta
    process = await db.processes.find_one(
        {"client_name": {"$regex": f"^{re.escape(client_name)}$", "$options": "i"}},
        {"_id": 0}
    )
    if process:
        return process
    
    # 3. Busca parcial - nome da pasta está contido no nome do cliente
    # Ex: pasta "João" encontra cliente "João e Maria" ou "João (Maria)"
    process = await db.processes.find_one(
        {"client_name": {"$regex": re.escape(client_name), "$options": "i"}},
        {"_id": 0}
    )
    if process:
        return process
    
    # 4. Busca inversa - nome do cliente está contido no nome da pasta
    # Procurar clientes cujo primeiro nome está no nome da pasta
    # Útil quando a pasta tem formato diferente
    all_processes = await db.processes.find(
        {},
        {"_id": 0, "id": 1, "client_name": 1}
    ).to_list(length=None)
    
    client_name_lower = client_name.lower()
    for proc in all_processes:
        proc_name = proc.get("client_name", "").lower()
        # Extrair primeiro nome do cliente
        first_name = proc_name.split()[0] if proc_name else ""
        # Extrair nomes de dentro de parênteses
        names_in_parens = re.findall(r'\(([^)]+)\)', proc_name)
        # Extrair nomes após "e" ou "/"
        names_after_sep = re.split(r'\s+e\s+|/|\(', proc_name)
        
        all_names = [first_name] + names_in_parens + [n.strip().split()[0].lower() for n in names_after_sep if n.strip()]
        
        for name in all_names:
            name = name.strip().lower()
            if name and len(name) > 2:  # Ignorar nomes muito curtos
                if name in client_name_lower or client_name_lower in name:
                    # Encontrado - buscar o documento completo
                    full_process = await db.processes.find_one(
                        {"id": proc["id"]},
                        {"_id": 0}
                    )
                    if full_process:
                        return full_process
    
    return None


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
        logger.info(f"update_client_data chamado: process_id={process_id}, document_type={document_type}")
        logger.info(f"extracted_data recebido: {extracted_data}")
        
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
        
        logger.info(f"update_data construído: {update_data}")
        
        # Aplicar actualização
        if len(update_data) > 1:
            result = await db.processes.update_one(
                {"id": process_id},
                {"$set": update_data}
            )
            logger.info(f"Update result: modified_count={result.modified_count}")
            return result.modified_count > 0
        else:
            logger.warning(f"update_data tem apenas {len(update_data)} campos, não actualizado")
        
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
    
    FUNCIONALIDADES:
    - Se detectar CC frente ou verso, guarda em cache e espera pelo outro
    - Quando tem frente+verso, junta num PDF e analisa
    - Normaliza nomes de ficheiros
    
    Estrutura do path: PastaRaiz/NomeCliente/[subpastas/]documento.pdf
    """
    filename = file.filename or "documento.pdf"
    
    # Extrair nome do cliente do path
    parts = filename.replace("\\", "/").split("/")
    
    if len(parts) >= 2:
        client_name = parts[1]
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
        # Ler ficheiro imediatamente
        content = await read_file_with_limit(file)
        mime_type = get_mime_type(doc_filename)
        
        # Procurar cliente
        process = await find_client_by_name(client_name)
        if not process:
            result.error = f"Cliente não encontrado: {client_name}"
            return result
        
        process_id = process.get("id")
        
        # Detectar tipo de documento
        document_type = detect_document_type(doc_filename)
        result.document_type = document_type
        
        # Nome normalizado
        normalized_name = get_normalized_filename(document_type)
        
        # Verificar se é CC frente ou verso
        if document_type == "cc":
            cc_side = is_cc_frente_or_verso(doc_filename)
            
            if cc_side:
                # Guardar em cache
                if process_id not in cc_cache:
                    cc_cache[process_id] = {}
                
                cc_cache[process_id][cc_side] = (content, mime_type)
                logger.info(f"CC {cc_side} guardado em cache para {client_name}")
                
                # Verificar se já temos frente E verso
                if "frente" in cc_cache[process_id] and "verso" in cc_cache[process_id]:
                    logger.info(f"CC completo (frente+verso) para {client_name}, a juntar...")
                    
                    # Juntar frente e verso num PDF
                    frente_data = cc_cache[process_id]["frente"]
                    verso_data = cc_cache[process_id]["verso"]
                    
                    merged_pdf = merge_images_to_pdf([frente_data, verso_data])
                    
                    if merged_pdf:
                        # Analisar o PDF combinado
                        merged_base64 = base64.b64encode(merged_pdf).decode('utf-8')
                        
                        analysis_result = await analyze_document_from_base64(
                            merged_base64,
                            "application/pdf",
                            "cc"
                        )
                        
                        # Limpar cache
                        del cc_cache[process_id]
                        
                        if analysis_result.get("success") or analysis_result.get("extracted_data"):
                            result.success = True
                            result.fields_extracted = list(analysis_result.get("extracted_data", {}).keys())
                            result.filename = normalized_name
                            
                            # Actualizar ficha do cliente
                            updated = await update_client_data(
                                process_id,
                                analysis_result.get("extracted_data", {}),
                                document_type
                            )
                            result.updated = updated
                            
                            logger.info(f"CC (frente+verso) analisado para {client_name}: {len(result.fields_extracted)} campos")
                        else:
                            result.error = analysis_result.get("error", "Erro na análise do CC combinado")
                    else:
                        result.error = "Erro ao juntar CC frente+verso"
                        del cc_cache[process_id]
                else:
                    # Ainda falta frente ou verso
                    result.success = True
                    result.filename = f"CC_{cc_side} (a aguardar {'verso' if cc_side == 'frente' else 'frente'})"
                    result.fields_extracted = []
                    logger.info(f"A aguardar {'verso' if cc_side == 'frente' else 'frente'} do CC para {client_name}")
                
                return result
        
        # Análise normal (não é CC frente/verso)
        analysis_result = await analyze_single_document(
            content=content,
            filename=doc_filename,
            client_name=client_name,
            process_id=process_id
        )
        
        if analysis_result.get("success") and analysis_result.get("extracted_data"):
            result.success = True
            result.fields_extracted = list(analysis_result["extracted_data"].keys())
            result.filename = normalized_name  # Nome normalizado
            
            # Actualizar ficha do cliente
            updated = await update_client_data(
                process_id,
                analysis_result["extracted_data"],
                document_type
            )
            result.updated = updated
            
            logger.info(f"Analisado {doc_filename} -> {normalized_name} para {client_name}: {len(result.fields_extracted)} campos")
        else:
            result.error = analysis_result.get("error", "Erro na análise")
            logger.warning(f"Falha ao analisar {doc_filename}: {result.error}")
        
    except ValueError as e:
        result.error = str(e)
    except Exception as e:
        result.error = f"Erro inesperado: {str(e)}"
        logger.error(f"Erro ao processar {filename}: {e}")
    
    return result


@router.get("/check-client")
async def check_client_exists(
    name: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Verificar se um cliente existe pelo nome.
    Usado para validar antes de processar ficheiros.
    """
    if not name:
        return {"exists": False, "client": None}
    
    process = await find_client_by_name(name)
    
    if process:
        return {
            "exists": True,
            "client": {
                "id": process.get("id"),
                "name": process.get("client_name"),
                "number": process.get("process_number")
            }
        }
    
    return {"exists": False, "client": None}


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
