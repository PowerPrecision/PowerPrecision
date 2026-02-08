"""
Bulk AI Document Analysis Routes
Upload de documentos para análise com IA e preenchimento automático das fichas de clientes.

IMPORTANTE: Os ficheiros são processados um a um pelo frontend.
O endpoint /analyze-single recebe e processa um ficheiro de cada vez.

FUNCIONALIDADES:
- Normalização de nomes de ficheiros
- Junção de CC frente+verso num único PDF para análise
- Conversão de PDFs scan para imagem
- Detecção de documentos duplicados (evita reanalisar recibos/extratos iguais)
- Matching flexível de nomes (suporta acentos, parênteses, nomes compostos)
"""
import os
import re
import uuid
import base64
import logging
import hashlib
import unicodedata
from typing import List, Optional, Dict, Tuple, Set
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

# Cache para hashes de documentos já analisados (evitar duplicados)
# Estrutura: {process_id: {document_type: {hash: extracted_data}}}
document_hash_cache: Dict[str, Dict[str, Dict[str, dict]]] = {}

# Tipos de documentos que tipicamente vêm em múltiplas cópias idênticas
# Expandido para incluir mais tipos comuns
DUPLICATE_PRONE_TYPES = {
    "recibo_vencimento",  # Recibos de vencimento mensais
    "extrato_bancario",   # Extratos bancários
    "recibo",             # Recibos genéricos
    "irs",                # Declarações IRS (mesmo ano)
    "contrato_trabalho",  # Contratos de trabalho
    "certidao",           # Certidões
}


def normalize_text_for_matching(text: str) -> str:
    """
    Normaliza texto para comparação de nomes.
    Remove acentos, converte para minúsculas, remove caracteres especiais.
    """
    if not text:
        return ""
    
    # Remover acentos
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Converter para minúsculas
    text = text.lower()
    
    # Remover caracteres especiais exceto espaços
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Normalizar espaços
    text = ' '.join(text.split())
    
    return text


def extract_all_names_from_string(text: str) -> Set[str]:
    """
    Extrai todos os nomes possíveis de uma string.
    Suporta formatos: "João e Maria", "João (Maria)", "João / Maria", "João, Maria"
    """
    names = set()
    if not text:
        return names
    
    # Extrair nomes de parênteses primeiro (ex: "Claúdia Batista (Edson)")
    parens_names = re.findall(r'\(([^)]+)\)', text)
    for name in parens_names:
        names.add(normalize_text_for_matching(name))
    
    # Remover conteúdo dos parênteses para processar o resto
    text_clean = re.sub(r'\([^)]+\)', '', text)
    text_clean = normalize_text_for_matching(text_clean)
    
    # Separar por delimitadores comuns
    separators = [' e ', ' / ', ', ', ' - ']
    parts = [text_clean]
    for sep in separators:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(sep))
        parts = new_parts
    
    for part in parts:
        part = part.strip()
        if part and len(part) > 2:
            names.add(part)
            # Adicionar também o primeiro nome
            first_name = part.split()[0] if part.split() else ""
            if first_name and len(first_name) > 2:
                names.add(first_name)
    
    return names


def calculate_document_hash(content: bytes) -> str:
    """Calcular hash MD5 do conteúdo do documento."""
    return hashlib.md5(content).hexdigest()


async def is_duplicate_document_db(process_id: str, document_type: str, doc_hash: str) -> Optional[dict]:
    """
    Verifica se o documento já foi analisado anteriormente (persistido na DB).
    
    Returns:
        Dados do documento se for duplicado, None caso contrário
    """
    process = await db.processes.find_one(
        {"id": process_id},
        {"_id": 0, "analyzed_documents": 1}
    )
    
    if not process:
        return None
    
    analyzed_docs = process.get("analyzed_documents", [])
    
    for doc in analyzed_docs:
        if doc.get("hash") == doc_hash:
            logger.info(f"Documento duplicado detectado (DB): hash={doc_hash[:8]}... para {process_id}")
            return doc
        
        # Verificar também por tipo + mês de referência (para recibos do mesmo mês)
        if doc.get("document_type") == document_type:
            if document_type in ["recibo_vencimento", "extrato_bancario"]:
                # Se já existe um recibo/extrato do mesmo tipo, pode ser duplicado
                # (verificado pelo hash acima)
                pass
    
    return None


def is_duplicate_document(process_id: str, document_type: str, content: bytes) -> Optional[dict]:
    """
    Verifica se o documento é duplicado de um já analisado (cache em memória).
    
    Returns:
        Dados extraídos anteriormente se for duplicado, None caso contrário
    """
    if document_type not in DUPLICATE_PRONE_TYPES:
        return None
    
    doc_hash = calculate_document_hash(content)
    
    if process_id in document_hash_cache:
        if document_type in document_hash_cache[process_id]:
            if doc_hash in document_hash_cache[process_id][document_type]:
                logger.info(f"Documento duplicado detectado (cache): {document_type} para {process_id}")
                return document_hash_cache[process_id][document_type][doc_hash]
    
    return None


async def check_duplicate_comprehensive(process_id: str, document_type: str, content: bytes) -> Optional[dict]:
    """
    Verificação completa de duplicados: cache em memória + base de dados.
    
    Returns:
        Dados do documento se for duplicado, None caso contrário
    """
    if document_type not in DUPLICATE_PRONE_TYPES:
        return None
    
    doc_hash = calculate_document_hash(content)
    
    # 1. Verificar cache em memória (rápido)
    cached = is_duplicate_document(process_id, document_type, content)
    if cached:
        return cached
    
    # 2. Verificar base de dados (persistente)
    db_record = await is_duplicate_document_db(process_id, document_type, doc_hash)
    if db_record:
        return db_record
    
    return None


def cache_document_analysis(process_id: str, document_type: str, content: bytes, extracted_data: dict):
    """Guardar resultado da análise em cache de memória para detectar duplicados futuros."""
    if document_type not in DUPLICATE_PRONE_TYPES:
        return
    
    doc_hash = calculate_document_hash(content)
    
    if process_id not in document_hash_cache:
        document_hash_cache[process_id] = {}
    if document_type not in document_hash_cache[process_id]:
        document_hash_cache[process_id][document_type] = {}
    
    document_hash_cache[process_id][document_type][doc_hash] = extracted_data


async def persist_document_analysis(process_id: str, document_type: str, content: bytes, extracted_data: dict, filename: str = ""):
    """
    Persistir registo de documento analisado na base de dados.
    Evita re-análise mesmo após reinício do servidor.
    """
    doc_hash = calculate_document_hash(content)
    
    # Extrair mês de referência se disponível (para recibos/extratos)
    mes_referencia = extracted_data.get("mes_referencia") or extracted_data.get("periodo") or ""
    
    doc_record = {
        "hash": doc_hash,
        "document_type": document_type,
        "filename": filename,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "mes_referencia": mes_referencia,
        "fields_extracted": list(extracted_data.keys()) if extracted_data else []
    }
    
    # Adicionar ao array analyzed_documents do processo
    await db.processes.update_one(
        {"id": process_id},
        {
            "$push": {"analyzed_documents": doc_record},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    logger.info(f"Documento persistido: {document_type} (hash={doc_hash[:8]}...) para {process_id}")


def validate_nif(nif: str) -> bool:
    """
    Valida se o NIF é válido.
    NIFs portugueses não podem começar por 0, 3, 4, 7, 8 (pessoas singulares começam por 1, 2, 5, 6).
    NIFs de empresas começam por 5.
    """
    if not nif:
        return True  # Permitir vazio
    
    # Remover espaços e caracteres não numéricos
    nif = re.sub(r'\D', '', str(nif))
    
    if len(nif) != 9:
        return False
    
    # Para pessoas singulares, NIF deve começar por 1, 2 ou 6
    # 5 é para empresas/colectividades
    first_digit = nif[0]
    
    # NIFs de clientes (pessoas singulares) tipicamente começam por 1, 2 ou 6
    # 5 é para entidades colectivas - provavelmente erro se aparecer como cliente
    if first_digit == '5':
        logger.warning(f"NIF {nif} começa por 5 (entidade colectiva) - possível erro")
        return False
    
    if first_digit not in ['1', '2', '6', '9']:  # 9 é para entidades internacionais
        logger.warning(f"NIF {nif} tem primeiro dígito inválido: {first_digit}")
        return False
    
    return True


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
    
    Suporta:
    - Nomes com/sem acentos: "Cláudia" encontra "Claudia"
    - Nomes compostos: "João e Maria", "João (Maria)", "João / Maria"
    - Nomes parciais: pasta "João" encontra cliente "João e Maria"
    - Nomes entre parênteses: "Claúdia Batista (Edson)" é encontrado por "Edson"
    """
    if not client_name:
        return None
    
    client_name = client_name.strip()
    client_name_normalized = normalize_text_for_matching(client_name)
    client_names = extract_all_names_from_string(client_name)
    
    logger.info(f"Procurando cliente: '{client_name}' | Normalizado: '{client_name_normalized}' | Nomes extraídos: {client_names}")
    
    # 1. Busca exacta (com acentos)
    process = await db.processes.find_one(
        {"client_name": client_name},
        {"_id": 0}
    )
    if process:
        logger.info(f"Cliente encontrado (exacto): {process.get('client_name')}")
        return process
    
    # 2. Busca case-insensitive exacta
    process = await db.processes.find_one(
        {"client_name": {"$regex": f"^{re.escape(client_name)}$", "$options": "i"}},
        {"_id": 0}
    )
    if process:
        logger.info(f"Cliente encontrado (case-insensitive): {process.get('client_name')}")
        return process
    
    # 3. Buscar todos os processos e fazer matching flexível
    all_processes = await db.processes.find(
        {},
        {"_id": 0, "id": 1, "client_name": 1}
    ).to_list(length=None)
    
    best_match = None
    best_score = 0
    
    for proc in all_processes:
        proc_name = proc.get("client_name", "")
        proc_name_normalized = normalize_text_for_matching(proc_name)
        proc_names = extract_all_names_from_string(proc_name)
        
        score = 0
        
        # Match exacto normalizado (sem acentos)
        if client_name_normalized == proc_name_normalized:
            score = 100
        
        # Match parcial - nome da pasta contido no nome do cliente
        elif client_name_normalized in proc_name_normalized:
            score = 80
        
        # Match parcial inverso - nome do cliente contido no nome da pasta
        elif proc_name_normalized in client_name_normalized:
            score = 75
        
        # Match de nomes individuais
        else:
            # Verificar se algum nome da pasta está no cliente
            common_names = client_names & proc_names
            if common_names:
                # Quanto mais nomes em comum, maior o score
                score = 50 + (len(common_names) * 10)
            else:
                # Verificar substrings (primeiro nome)
                for cn in client_names:
                    for pn in proc_names:
                        if cn and pn and len(cn) > 2 and len(pn) > 2:
                            if cn in pn or pn in cn:
                                score = max(score, 40)
        
        if score > best_score:
            best_score = score
            best_match = proc
            logger.debug(f"Novo melhor match: '{proc_name}' com score {score}")
    
    if best_match and best_score >= 40:
        # Buscar documento completo
        full_process = await db.processes.find_one(
            {"id": best_match["id"]},
            {"_id": 0}
        )
        if full_process:
            logger.info(f"Cliente encontrado (fuzzy, score={best_score}): '{best_match.get('client_name')}' para '{client_name}'")
            return full_process
    
    logger.warning(f"Cliente não encontrado: '{client_name}' (melhor score: {best_score})")
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


async def update_client_data(process_id: str, extracted_data: dict, document_type: str) -> Tuple[bool, List[str]]:
    """
    Actualizar ficha do cliente com dados extraídos.
    
    Returns:
        Tuple de (success, list of updated fields)
    """
    updated_fields = []
    
    try:
        logger.info(f"update_client_data: process_id={process_id}, document_type={document_type}")
        logger.info(f"extracted_data: {list(extracted_data.keys())}")
        
        # Validar NIF antes de guardar
        nif = extracted_data.get('nif') or extracted_data.get('NIF')
        if nif and not validate_nif(nif):
            logger.warning(f"NIF inválido rejeitado: {nif}")
            if 'nif' in extracted_data:
                del extracted_data['nif']
            if 'NIF' in extracted_data:
                del extracted_data['NIF']
        
        # Obter dados existentes
        process = await db.processes.find_one(
            {"id": process_id},
            {"_id": 0, "personal_data": 1, "financial_data": 1, "real_estate_data": 1, "ai_extracted_notes": 1, "client_name": 1}
        )
        
        if not process:
            logger.error(f"Processo não encontrado: {process_id}")
            return False, []
        
        # Construir dados de actualização
        update_data = build_update_data_from_extraction(
            extracted_data,
            document_type,
            process or {}
        )
        
        # Identificar campos que serão actualizados
        for key, value in update_data.items():
            if key != "updated_at" and value:
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        if subvalue:
                            updated_fields.append(f"{key}.{subkey}")
                else:
                    updated_fields.append(key)
        
        logger.info(f"Campos a actualizar: {updated_fields}")
        
        # Aplicar actualização
        if len(update_data) > 1:
            result = await db.processes.update_one(
                {"id": process_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Cliente '{process.get('client_name')}' actualizado com sucesso! Campos: {updated_fields}")
                return True, updated_fields
            else:
                # Verificar se os dados já eram iguais
                logger.info("Nenhuma alteração necessária (dados já existentes)")
                return True, updated_fields
        else:
            logger.warning(f"Nenhum dado para actualizar (update_data tem apenas {len(update_data)} campos)")
        
        return False, []
        
    except Exception as e:
        logger.error(f"Erro ao actualizar cliente {process_id}: {e}", exc_info=True)
        return False, []


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
    - Detecta documentos duplicados (ex: 3 recibos de vencimento iguais)
    - Validação melhorada de NIF
    
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
            result.error = f"Cliente não encontrado: {client_name}. Verifique se o nome está correcto (acentos, parênteses)."
            logger.warning(f"Cliente não encontrado para '{client_name}'. Pasta: {filename}")
            return result
        
        process_id = process.get("id")
        actual_client_name = process.get("client_name", client_name)
        result.client_name = actual_client_name  # Usar nome real do cliente
        
        # Detectar tipo de documento
        document_type = detect_document_type(doc_filename)
        result.document_type = document_type
        
        # Verificar se é documento duplicado (cache + DB)
        duplicate_data = await check_duplicate_comprehensive(process_id, document_type, content)
        if duplicate_data:
            logger.info(f"Documento duplicado detectado para {actual_client_name}: {document_type}")
            result.success = True
            result.error = "Documento idêntico já analisado anteriormente (ignorado)"
            return result
        
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
                logger.info(f"CC {cc_side} guardado em cache para {actual_client_name}")
                
                # Verificar se já temos frente E verso
                if "frente" in cc_cache[process_id] and "verso" in cc_cache[process_id]:
                    logger.info(f"CC completo (frente+verso) para {actual_client_name}, a juntar...")
                    
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
                            
                            # Persistir análise do CC na DB
                            await persist_document_analysis(
                                process_id,
                                "cc",
                                merged_pdf,
                                analysis_result.get("extracted_data", {}),
                                "CC_frente_verso.pdf"
                            )
                            
                            # Actualizar ficha do cliente
                            updated, fields = await update_client_data(
                                process_id,
                                analysis_result.get("extracted_data", {}),
                                document_type
                            )
                            result.updated = updated
                            
                            logger.info(f"CC (frente+verso) analisado para {actual_client_name}: {len(result.fields_extracted)} campos, actualizados: {fields}")
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
                    logger.info(f"A aguardar {'verso' if cc_side == 'frente' else 'frente'} do CC para {actual_client_name}")
                
                return result
        
        # Análise normal (não é CC frente/verso)
        analysis_result = await analyze_single_document(
            content=content,
            filename=doc_filename,
            client_name=actual_client_name,
            process_id=process_id
        )
        
        if analysis_result.get("success") and analysis_result.get("extracted_data"):
            result.success = True
            result.fields_extracted = list(analysis_result["extracted_data"].keys())
            result.filename = normalized_name  # Nome normalizado
            
            # Guardar em cache (memória) para detectar duplicados durante a sessão
            cache_document_analysis(process_id, document_type, content, analysis_result["extracted_data"])
            
            # Persistir na DB para detectar duplicados após reinício
            await persist_document_analysis(
                process_id, 
                document_type, 
                content, 
                analysis_result["extracted_data"],
                doc_filename
            )
            
            # Actualizar ficha do cliente
            updated, fields = await update_client_data(
                process_id,
                analysis_result["extracted_data"],
                document_type
            )
            result.updated = updated
            
            logger.info(f"✅ {doc_filename} -> {normalized_name} para '{actual_client_name}': {len(result.fields_extracted)} campos extraídos, {len(fields)} actualizados")
        else:
            result.error = analysis_result.get("error", "Erro na análise")
            logger.warning(f"❌ Falha ao analisar {doc_filename}: {result.error}")
        
    except ValueError as e:
        result.error = str(e)
    except Exception as e:
        result.error = f"Erro inesperado: {str(e)}"
        logger.error(f"Erro ao processar {filename}: {e}", exc_info=True)
    
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



@router.get("/diagnose-client/{client_name}")
async def diagnose_client_data(
    client_name: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Diagnóstico de dados de um cliente.
    Mostra quais campos estão preenchidos e quais estão vazios.
    """
    process = await find_client_by_name(client_name)
    
    if not process:
        return {
            "found": False,
            "error": f"Cliente '{client_name}' não encontrado"
        }
    
    # Verificar campos preenchidos
    personal = process.get("personal_data", {})
    financial = process.get("financial_data", {})
    real_estate = process.get("real_estate_data", {})
    
    def count_filled(data: dict) -> Tuple[int, int, list]:
        if not data:
            return 0, 0, []
        filled = [(k, v) for k, v in data.items() if v is not None and v != ""]
        return len(filled), len(data), [k for k, _ in filled]
    
    personal_filled, personal_total, personal_fields = count_filled(personal)
    financial_filled, financial_total, financial_fields = count_filled(financial)
    real_estate_filled, real_estate_total, real_estate_fields = count_filled(real_estate)
    
    return {
        "found": True,
        "client_name": process.get("client_name"),
        "process_id": process.get("id"),
        "summary": {
            "personal_data": f"{personal_filled}/{personal_total} campos",
            "financial_data": f"{financial_filled}/{financial_total} campos",
            "real_estate_data": f"{real_estate_filled}/{real_estate_total} campos",
        },
        "filled_fields": {
            "personal": personal_fields,
            "financial": financial_fields,
            "real_estate": real_estate_fields,
        },
        "raw_data": {
            "email": process.get("client_email"),
            "phone": process.get("client_phone"),
            "personal_data": personal,
            "financial_data": financial,
        }
    }


@router.post("/clear-duplicate-cache")
async def clear_duplicate_cache(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Limpar cache de documentos duplicados."""
    global document_hash_cache
    count = sum(
        sum(len(hashes) for hashes in types.values())
        for types in document_hash_cache.values()
    )
    document_hash_cache = {}
    return {"message": f"Cache limpo. {count} documentos removidos do cache."}
