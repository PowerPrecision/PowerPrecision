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

SEGURANÇA:
- Validação de ficheiros usando Magic Bytes (não confia na extensão)
- Whitelist de MIME types permitidos (PDF, JPEG, PNG, etc.)
- Bloqueio de ficheiros executáveis e scripts
"""
import os
import re
import uuid
import base64
import logging
import hashlib
import unicodedata
from typing import List, Optional, Dict, Tuple, Set, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from database import db
from models.auth import UserRole
from services.auth import require_roles, get_current_user
from services.file_validation import validate_file_content, validate_file_upload
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
from services.documents.data_aggregator import (
    get_or_create_session,
    get_session,
    get_session_async,
    close_session,
    persist_session_to_db,
    SessionAggregator,
    ClientDataAggregator
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/bulk", tags=["AI Bulk Analysis"])

# ====================================================================
# TRACKING DE PROCESSOS EM BACKGROUND (Item 2 - Outros erros/melhorias)
# ====================================================================
# Cache em memória para performance (a DB é a fonte de verdade)
background_processes: Dict[str, dict] = {}  # job_id -> status


async def create_background_job_db(job_type: str, user_email: str, details: dict = None, total_files: int = 0) -> str:
    """Criar registo de job em background (persistido na DB)."""
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "type": job_type,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "user_email": user_email,
        "progress": 0,
        "total": total_files,
        "processed": 0,
        "errors": 0,
        "details": details or {},
        "error_messages": [],
        "finished_at": None
    }
    
    # Guardar em memória e na DB
    background_processes[job_id] = job
    await db.background_jobs.insert_one({**job, "_id": job_id})
    
    logger.info(f"Job background criado: {job_id} ({job_type}) com {total_files} ficheiros")
    return job_id


async def update_background_job_db(job_id: str, **kwargs):
    """Atualizar estado de um job em background (persistido na DB)."""
    # Calcular progresso percentual se houver total
    update_data = {**kwargs, "updated_at": datetime.now(timezone.utc).isoformat()}
    
    # Actualizar cache em memória
    if job_id in background_processes:
        background_processes[job_id].update(update_data)
        if background_processes[job_id].get("total", 0) > 0:
            processed = background_processes[job_id].get("processed", 0)
            total = background_processes[job_id]["total"]
            update_data["progress"] = int((processed / total) * 100)
            background_processes[job_id]["progress"] = update_data["progress"]
    
    # Actualizar na DB
    await db.background_jobs.update_one(
        {"id": job_id},
        {"$set": update_data}
    )


async def finish_background_job_db(job_id: str, success: bool, message: str = None):
    """Marcar job como terminado (persistido na DB)."""
    status = "success" if success else "failed"
    finished_at = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "status": status,
        "finished_at": finished_at
    }
    if message:
        update_data["message"] = message
    
    # Actualizar cache em memória
    if job_id in background_processes:
        background_processes[job_id].update(update_data)
    
    # Actualizar na DB
    await db.background_jobs.update_one(
        {"id": job_id},
        {"$set": update_data}
    )
    
    logger.info(f"Job background terminado: {job_id} ({status})")


async def load_background_jobs_from_db():
    """Carregar jobs da DB para memória (chamado no startup)."""
    global background_processes
    try:
        # Carregar apenas jobs recentes (últimos 7 dias)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        jobs = await db.background_jobs.find(
            {"started_at": {"$gte": cutoff}},
            {"_id": 0}
        ).to_list(100)
        
        for job in jobs:
            background_processes[job["id"]] = job
        
        logger.info(f"[BACKGROUND JOBS] {len(jobs)} jobs carregados da DB")
    except Exception as e:
        logger.error(f"[BACKGROUND JOBS] Erro ao carregar da DB: {e}")


# Funções legadas para compatibilidade (usam as novas funções async)
def create_background_job(job_type: str, user_email: str, details: dict = None) -> str:
    """[LEGACY] Criar registo de job em background (apenas memória)."""
    job_id = str(uuid.uuid4())
    background_processes[job_id] = {
        "id": job_id,
        "type": job_type,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "user_email": user_email,
        "progress": 0,
        "total": 0,
        "processed": 0,
        "errors": 0,
        "details": details or {},
        "error_messages": [],
        "finished_at": None
    }
    logger.info(f"Job background criado (legacy): {job_id} ({job_type})")
    return job_id


def update_background_job(job_id: str, **kwargs):
    """[LEGACY] Atualizar estado de um job em background (apenas memória)."""
    if job_id in background_processes:
        background_processes[job_id].update(kwargs)
        
        # Calcular progresso percentual
        if background_processes[job_id].get("total", 0) > 0:
            processed = background_processes[job_id].get("processed", 0)
            total = background_processes[job_id]["total"]
            background_processes[job_id]["progress"] = int((processed / total) * 100)


def finish_background_job(job_id: str, success: bool, message: str = None):
    """[LEGACY] Marcar job como terminado (apenas memória)."""
    if job_id in background_processes:
        background_processes[job_id]["status"] = "success" if success else "failed"
        background_processes[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
        if message:
            background_processes[job_id]["message"] = message
        logger.info(f"Job background terminado (legacy): {job_id} ({background_processes[job_id]['status']})")


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

# ====================================================================
# CACHE DE SESSÃO NIF - Mapeamento Pasta → Cliente (Item 17)
# ====================================================================
# Quando um CC é analisado e o NIF extraído, guarda o mapeamento
# pasta → cliente para documentos subsequentes da mesma pasta.
# PERSISTÊNCIA: Os mapeamentos são guardados na coleção 'nif_mappings' da DB
# para sobreviver a reinícios do servidor.
# Estrutura em memória: {folder_name_normalized: {
#     "nif": "123456789",
#     "process_id": "uuid",
#     "client_name": "Nome Cliente",
#     "matched_at": datetime
# }}
nif_session_cache: Dict[str, Dict[str, Any]] = {}

# Tempo máximo de validade do cache NIF (30 dias para persistência)
NIF_CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 dias

# Flag para saber se já carregámos o cache da DB
_nif_cache_loaded = False


def get_nif_cache_key(folder_name: str) -> str:
    """Gerar chave normalizada para o cache de NIF."""
    return normalize_text_for_matching(folder_name)


async def _load_nif_cache_from_db():
    """Carregar mapeamentos NIF da base de dados para memória."""
    global nif_session_cache, _nif_cache_loaded
    
    if _nif_cache_loaded:
        return
    
    try:
        mappings = await db.nif_mappings.find({}, {"_id": 0}).to_list(1000)
        
        for mapping in mappings:
            cache_key = mapping.get("cache_key")
            if cache_key:
                # Converter string ISO para datetime
                matched_at = mapping.get("matched_at")
                if isinstance(matched_at, str):
                    matched_at = datetime.fromisoformat(matched_at.replace("Z", "+00:00"))
                
                nif_session_cache[cache_key] = {
                    "nif": mapping.get("nif"),
                    "process_id": mapping.get("process_id"),
                    "client_name": mapping.get("client_name"),
                    "matched_at": matched_at
                }
        
        _nif_cache_loaded = True
        logger.info(f"[NIF CACHE] {len(mappings)} mapeamentos carregados da base de dados")
    except Exception as e:
        logger.error(f"[NIF CACHE] Erro ao carregar da DB: {e}")


async def cache_nif_mapping(folder_name: str, nif: str, process_id: str, client_name: str):
    """
    Guardar mapeamento NIF → Cliente no cache de sessão E na base de dados.
    
    Args:
        folder_name: Nome da pasta do documento
        nif: NIF extraído do CC
        process_id: ID do processo/cliente na DB
        client_name: Nome do cliente
    """
    cache_key = get_nif_cache_key(folder_name)
    now = datetime.now(timezone.utc)
    
    # Guardar em memória
    nif_session_cache[cache_key] = {
        "nif": nif,
        "process_id": process_id,
        "client_name": client_name,
        "matched_at": now
    }
    
    # Persistir na base de dados (upsert)
    try:
        await db.nif_mappings.update_one(
            {"cache_key": cache_key},
            {"$set": {
                "cache_key": cache_key,
                "folder_name": folder_name,
                "nif": nif,
                "process_id": process_id,
                "client_name": client_name,
                "matched_at": now.isoformat(),
                "updated_at": now.isoformat()
            }},
            upsert=True
        )
        logger.info(f"[NIF CACHE] Mapeamento guardado (memória + DB): '{folder_name}' -> NIF {nif} -> '{client_name}'")
    except Exception as e:
        logger.error(f"[NIF CACHE] Erro ao persistir na DB: {e}")


async def get_cached_nif_mapping(folder_name: str) -> Optional[Dict[str, Any]]:
    """
    Obter mapeamento do cache de sessão NIF.
    Primeiro verifica memória, depois a base de dados.
    
    Returns:
        Dict com {nif, process_id, client_name} ou None se não existe/expirou
    """
    # Garantir que carregámos o cache da DB
    await _load_nif_cache_from_db()
    
    cache_key = get_nif_cache_key(folder_name)
    cached = nif_session_cache.get(cache_key)
    
    # Se não está em memória, tentar buscar da DB
    if not cached:
        try:
            db_mapping = await db.nif_mappings.find_one({"cache_key": cache_key}, {"_id": 0})
            if db_mapping:
                matched_at = db_mapping.get("matched_at")
                if isinstance(matched_at, str):
                    matched_at = datetime.fromisoformat(matched_at.replace("Z", "+00:00"))
                
                cached = {
                    "nif": db_mapping.get("nif"),
                    "process_id": db_mapping.get("process_id"),
                    "client_name": db_mapping.get("client_name"),
                    "matched_at": matched_at
                }
                # Adicionar ao cache de memória
                nif_session_cache[cache_key] = cached
                logger.info(f"[NIF CACHE] Mapeamento carregado da DB: '{folder_name}'")
        except Exception as e:
            logger.error(f"[NIF CACHE] Erro ao buscar da DB: {e}")
            return None
    
    if not cached:
        return None
    
    # Verificar se expirou (30 dias)
    matched_at = cached.get("matched_at")
    if matched_at:
        if isinstance(matched_at, str):
            matched_at = datetime.fromisoformat(matched_at.replace("Z", "+00:00"))
        
        age = (datetime.now(timezone.utc) - matched_at).total_seconds()
        if age > NIF_CACHE_TTL_SECONDS:
            logger.info(f"[NIF CACHE] Mapeamento expirado para '{folder_name}' (idade: {int(age/86400)} dias)")
            # Remover da memória e da DB
            del nif_session_cache[cache_key]
            await db.nif_mappings.delete_one({"cache_key": cache_key})
            return None
    
    logger.info(f"[NIF CACHE] Hit para '{folder_name}': NIF {cached.get('nif')} -> '{cached.get('client_name')}'")
    return cached


async def find_client_by_nif(nif: str) -> Optional[dict]:
    """
    Encontrar cliente pelo NIF (busca exacta na DB).
    
    O NIF é o método mais fiável para ligar documentos a clientes,
    pois é único e imutável.
    
    Args:
        nif: Número de Identificação Fiscal (9 dígitos)
        
    Returns:
        Processo/cliente completo ou None
    """
    if not nif:
        return None
    
    # Limpar NIF (apenas dígitos)
    nif_clean = re.sub(r'\D', '', str(nif))
    
    if len(nif_clean) != 9:
        logger.warning(f"[NIF] NIF inválido (não tem 9 dígitos): {nif}")
        return None
    
    # Buscar em personal_data.nif
    process = await db.processes.find_one(
        {"personal_data.nif": nif_clean},
        {"_id": 0}
    )
    
    if process:
        logger.info(f"[NIF] Cliente encontrado por NIF {nif_clean}: '{process.get('client_name')}'")
        return process
    
    # Buscar também no campo client_nif (se existir)
    process = await db.processes.find_one(
        {"client_nif": nif_clean},
        {"_id": 0}
    )
    
    if process:
        logger.info(f"[NIF] Cliente encontrado por client_nif {nif_clean}: '{process.get('client_name')}'")
        return process
    
    logger.info(f"[NIF] Nenhum cliente encontrado com NIF {nif_clean}")
    return None


async def clear_expired_nif_cache():
    """Limpar entradas expiradas do cache NIF (memória e DB)."""
    now = datetime.now(timezone.utc)
    expired_keys = []
    
    for key, cached in nif_session_cache.items():
        matched_at = cached.get("matched_at")
        if matched_at:
            if isinstance(matched_at, str):
                matched_at = datetime.fromisoformat(matched_at.replace("Z", "+00:00"))
            age = (now - matched_at).total_seconds()
            if age > NIF_CACHE_TTL_SECONDS:
                expired_keys.append(key)
    
    for key in expired_keys:
        del nif_session_cache[key]
        # Remover também da DB
        await db.nif_mappings.delete_one({"cache_key": key})
    
    if expired_keys:
        logger.info(f"[NIF CACHE] Limpeza: {len(expired_keys)} entradas expiradas removidas")


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
    # CORREÇÃO DE SEGURANÇA: Adicionado usedforsecurity=False
    return hashlib.md5(content, usedforsecurity=False).hexdigest()


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
    Valida se o NIF é válido para pessoa singular.
    NIFs de pessoas singulares começam por 1, 2, 6 ou 9.
    NIFs começados por 5 são de empresas/colectividades - REJEITADOS.
    """
    if not nif:
        return True  # Permitir vazio
    
    # Remover espaços e caracteres não numéricos
    nif = re.sub(r'\D', '', str(nif))
    
    if len(nif) != 9:
        return False
    
    # Rejeitar NIFs placeholder
    if nif in ['123456789', '000000000', '111111111', '999999999']:
        logger.warning(f"NIF {nif} é um placeholder - rejeitado")
        return False
    
    first_digit = nif[0]
    
    # 5 é para entidades colectivas - SEMPRE REJEITAR para clientes
    if first_digit == '5':
        logger.warning(f"NIF {nif} começa por 5 (entidade colectiva) - REJEITADO")
        return False
    
    # NIFs válidos para pessoas singulares: 1, 2, 6, 9
    if first_digit not in ['1', '2', '6', '9']:
        logger.warning(f"NIF {nif} tem primeiro dígito inválido: {first_digit}")
        return False
    
    return True


def is_placeholder_value(value: str) -> bool:
    """Verifica se um valor é um placeholder (não real)."""
    if not value:
        return False
    
    value_str = str(value).strip().upper()
    
    # Datas placeholder
    if value_str in ['YYYY-MM-DD', 'DD/MM/YYYY', 'DD-MM-YYYY', 'N/A', 'NA', 'NULL', 'NONE', '']:
        return True
    
    # Valores numéricos placeholder
    if value_str in ['123456789', '000000000', '0', '00000000', '12345678']:
        return True
    
    # Se contém YYYY ou DD sem ser uma data real
    if 'YYYY' in value_str or value_str == 'DD':
        return True
    
    return False


def clean_extracted_value(value):
    """Limpa um valor extraído, removendo placeholders."""
    if value is None:
        return None
    
    if isinstance(value, str):
        if is_placeholder_value(value):
            return None
        return value.strip() if value.strip() else None
    
    return value


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
    conflicts: Optional[Dict[str, Any]] = None  # Campos com conflitos (não sobrescritos)


async def find_client_by_name(client_name: str) -> Optional[dict]:
    """
    Encontrar cliente pelo nome (busca flexível com FuzzyWuzzy).
    
    Melhorias (Item 13):
    - Usa fuzzywuzzy token_set_ratio para comparação fonética
    - Matching de primeiro nome com peso extra (+20)
    - Suporte melhorado para parênteses e nomes compostos
    - Score mínimo de 70 para aceitar match (era 40)
    
    Suporta:
    - Nomes com/sem acentos: "Cláudia" encontra "Claudia"
    - Nomes compostos: "João e Maria", "João (Maria)", "João / Maria"
    - Nomes parciais: pasta "João" encontra cliente "João e Maria"
    - Nomes entre parênteses: "Claúdia Batista (Edson)" é encontrado por "Edson"
    """
    if not client_name:
        return None
    
    # Importar fuzzywuzzy para matching fonético
    try:
        from fuzzywuzzy import fuzz
        HAS_FUZZY = True
    except ImportError:
        logger.warning("fuzzywuzzy não instalado - usando matching básico")
        HAS_FUZZY = False
    
    client_name = client_name.strip()
    client_name_normalized = normalize_text_for_matching(client_name)
    client_names = extract_all_names_from_string(client_name)
    
    # Extrair primeiro nome para matching com peso extra
    client_first_name = client_name_normalized.split()[0] if client_name_normalized.split() else ""
    
    logger.info(f"Procurando cliente: '{client_name}' | Normalizado: '{client_name_normalized}' | Primeiro nome: '{client_first_name}' | Nomes extraídos: {client_names}")
    
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
        {"_id": 0, "id": 1, "client_name": 1, "personal_data.nif": 1}
    ).to_list(length=None)
    
    best_match = None
    best_score = 0
    match_details = {}
    
    for proc in all_processes:
        proc_name = proc.get("client_name", "")
        proc_name_normalized = normalize_text_for_matching(proc_name)
        proc_names = extract_all_names_from_string(proc_name)
        
        # Extrair primeiro nome do cliente DB
        proc_first_name = proc_name_normalized.split()[0] if proc_name_normalized.split() else ""
        
        score = 0
        match_reason = ""
        
        # === Match exacto normalizado (sem acentos) ===
        if client_name_normalized == proc_name_normalized:
            score = 100
            match_reason = "exacto_normalizado"
        
        # === Match parcial - nome da pasta contido no nome do cliente ===
        elif client_name_normalized in proc_name_normalized:
            score = 85
            match_reason = "contido_no_cliente"
        
        # === Match parcial inverso - nome do cliente contido no nome da pasta ===
        elif proc_name_normalized in client_name_normalized:
            score = 80
            match_reason = "cliente_contido"
        
        # === FuzzyWuzzy token_set_ratio (Item 13) ===
        elif HAS_FUZZY:
            # token_set_ratio é bom para nomes em ordens diferentes
            fuzzy_score = fuzz.token_set_ratio(client_name_normalized, proc_name_normalized)
            
            # Bónus para primeiro nome igual (+20)
            first_name_bonus = 0
            if client_first_name and proc_first_name:
                if client_first_name == proc_first_name:
                    first_name_bonus = 20
                    logger.debug(f"Primeiro nome match: '{client_first_name}' -> '{proc_name}'")
                elif fuzz.ratio(client_first_name, proc_first_name) > 85:
                    first_name_bonus = 15
            
            score = min(fuzzy_score + first_name_bonus, 95)  # Cap em 95 para não ultrapassar match exacto
            match_reason = f"fuzzy_{fuzzy_score}+bonus_{first_name_bonus}"
        
        # === Match de nomes individuais (fallback) ===
        else:
            # Verificar se algum nome da pasta está no cliente
            common_names = client_names & proc_names
            if common_names:
                # Quanto mais nomes em comum, maior o score
                score = 55 + (len(common_names) * 10)
                match_reason = f"nomes_comuns_{len(common_names)}"
            else:
                # Verificar substrings (primeiro nome)
                for cn in client_names:
                    for pn in proc_names:
                        if cn and pn and len(cn) > 2 and len(pn) > 2:
                            if cn in pn or pn in cn:
                                score = max(score, 45)
                                match_reason = f"substring_{cn}_{pn}"
        
        if score > best_score:
            best_score = score
            best_match = proc
            match_details = {
                "proc_name": proc_name,
                "score": score,
                "reason": match_reason
            }
            logger.debug(f"Novo melhor match: '{proc_name}' com score {score} ({match_reason})")
    
    # Score mínimo de 70 (aumentado de 40 para reduzir falsos positivos)
    MIN_SCORE = 70
    
    if best_match and best_score >= MIN_SCORE:
        # Buscar documento completo
        full_process = await db.processes.find_one(
            {"id": best_match["id"]},
            {"_id": 0}
        )
        if full_process:
            logger.info(f"Cliente encontrado (fuzzy, score={best_score}): '{best_match.get('client_name')}' para '{client_name}' [{match_details.get('reason')}]")
            return full_process
    
    logger.warning(f"Cliente não encontrado: '{client_name}' (melhor score: {best_score}, min: {MIN_SCORE})")
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


async def update_client_data(process_id: str, extracted_data: dict, document_type: str, force_update: bool = False) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Actualizar ficha do cliente com dados extraídos.
    
    REGRAS IMPORTANTES:
    1. Processos concluídos/desistidos/cancelados: NÃO actualizar (retorna conflitos para revisão)
    2. Campos preenchidos manualmente pelo utilizador: NÃO sobrescrever (a menos que force_update=True)
    3. Guarda dados extraídos para comparação posterior
    
    Returns:
        Tuple de (success, list of updated fields, dict of conflicts/skipped)
    """
    updated_fields = []
    conflicts = {}  # Campos onde há diferença entre dados existentes e extraídos
    
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
            {"_id": 0}
        )
        
        if not process:
            logger.error(f"Processo não encontrado: {process_id}")
            return False, [], {"error": "Processo não encontrado"}
        
        # =====================================================================
        # REGRA 1: Processos finalizados não são actualizados
        # =====================================================================
        process_status = process.get("status", "")
        if process_status in ["concluido", "desistido", "cancelado", "arquivado"]:
            logger.info(f"Processo {process_id} está '{process_status}' - dados guardados para revisão apenas")
            
            # Guardar dados extraídos para revisão manual (sem actualizar o processo)
            await db.processes.update_one(
                {"id": process_id},
                {
                    "$push": {
                        "ai_pending_review": {
                            "document_type": document_type,
                            "extracted_data": extracted_data,
                            "extracted_at": datetime.now(timezone.utc).isoformat(),
                            "status": "pending_review"
                        }
                    }
                }
            )
            
            return True, [], {
                "status": "pending_review",
                "message": f"Processo '{process_status}' - dados guardados para revisão manual",
                "extracted_fields": list(extracted_data.keys())
            }
        
        # =====================================================================
        # REGRA 2: Não sobrescrever dados introduzidos manualmente
        # =====================================================================
        # Campos que foram editados manualmente têm metadata
        manually_edited = process.get("manually_edited_fields", [])
        
        # Construir dados de actualização
        update_data = build_update_data_from_extraction(
            extracted_data,
            document_type,
            process or {}
        )
        
        # Filtrar campos editados manualmente (a menos que force_update=True)
        if not force_update and manually_edited:
            for field in manually_edited:
                # Verificar se o campo está nos dados a actualizar
                if "." in field:
                    parent, child = field.split(".", 1)
                    if parent in update_data and isinstance(update_data[parent], dict):
                        if child in update_data[parent]:
                            old_value = process.get(parent, {}).get(child)
                            new_value = update_data[parent][child]
                            if old_value != new_value:
                                conflicts[field] = {
                                    "existing": old_value,
                                    "extracted": new_value,
                                    "reason": "Campo editado manualmente"
                                }
                            del update_data[parent][child]
                            logger.info(f"Campo '{field}' preservado (editado manualmente)")
                else:
                    if field in update_data:
                        old_value = process.get(field)
                        new_value = update_data[field]
                        if old_value != new_value:
                            conflicts[field] = {
                                "existing": old_value,
                                "extracted": new_value,
                                "reason": "Campo editado manualmente"
                            }
                        del update_data[field]
                        logger.info(f"Campo '{field}' preservado (editado manualmente)")
        
        # Identificar campos que serão actualizados
        for key, value in update_data.items():
            if key != "updated_at" and value:
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        if subvalue:
                            updated_fields.append(f"{key}.{subkey}")
                elif isinstance(value, list):
                    updated_fields.append(f"{key} ({len(value)} items)")
                else:
                    updated_fields.append(key)
        
        logger.info(f"Campos a actualizar: {updated_fields}")
        
        # =====================================================================
        # REGRA 3: Guardar dados extraídos para comparação posterior
        # =====================================================================
        # Guardar os dados extraídos num campo separado para revisão/comparação
        ai_extraction_log = {
            "document_type": document_type,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "extracted_data": extracted_data,
            "applied_fields": updated_fields,
            "conflicts": conflicts if conflicts else None
        }
        
        # Aplicar actualização
        if len(update_data) > 1:
            result = await db.processes.update_one(
                {"id": process_id},
                {
                    "$set": update_data,
                    "$push": {"ai_extraction_history": ai_extraction_log}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Cliente '{process.get('client_name')}' actualizado com sucesso! Campos: {updated_fields}")
                if conflicts:
                    logger.info(f"⚠️ Campos com conflitos (preservados): {list(conflicts.keys())}")
                return True, updated_fields, conflicts
            else:
                # Verificar se os dados já eram iguais
                logger.info("Nenhuma alteração necessária (dados já existentes)")
                return True, updated_fields, conflicts
        else:
            logger.warning(f"Nenhum dado para actualizar (update_data tem apenas {len(update_data)} campos)")
        
        return False, [], conflicts
        
    except Exception as e:
        logger.error(f"Erro ao actualizar cliente {process_id}: {e}", exc_info=True)
        return False, [], {"error": str(e)}



# ====================================================================
# ENDPOINTS DE SESSÃO DE IMPORTAÇÃO (P1 - Background Jobs)
# ====================================================================

class ImportSessionRequest(BaseModel):
    total_files: int
    folder_name: Optional[str] = None
    client_id: Optional[str] = None


class ImportSessionResponse(BaseModel):
    session_id: str
    message: str


@router.post("/import-session/start", response_model=ImportSessionResponse)
async def start_import_session(
    request: ImportSessionRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Iniciar uma sessão de importação em massa.
    Cria um job de background para tracking do progresso.
    
    O frontend deve chamar este endpoint antes de começar a enviar ficheiros.
    """
    details = {
        "folder_name": request.folder_name,
        "client_id": request.client_id
    }
    
    session_id = await create_background_job_db(
        job_type="bulk_import",
        user_email=user.get("email"),
        details=details,
        total_files=request.total_files
    )
    
    return ImportSessionResponse(
        session_id=session_id,
        message=f"Sessão de importação iniciada com {request.total_files} ficheiros"
    )


class UpdateSessionRequest(BaseModel):
    processed: Optional[int] = None
    errors: Optional[int] = None
    error_message: Optional[str] = None


@router.post("/import-session/{session_id}/update")
async def update_import_session(
    session_id: str,
    request: UpdateSessionRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Actualizar o progresso de uma sessão de importação.
    """
    update_fields = {}
    if request.processed is not None:
        update_fields["processed"] = request.processed
    if request.errors is not None:
        update_fields["errors"] = request.errors
    if request.error_message:
        # Adicionar à lista de mensagens de erro
        if session_id in background_processes:
            error_messages = background_processes[session_id].get("error_messages", [])
            error_messages.append(request.error_message)
            update_fields["error_messages"] = error_messages[-50:]  # Manter últimas 50
    
    if update_fields:
        await update_background_job_db(session_id, **update_fields)
    
    # Retornar estado actual
    job = background_processes.get(session_id) or await db.background_jobs.find_one({"id": session_id}, {"_id": 0})
    return job or {"error": "Sessão não encontrada"}


@router.post("/import-session/{session_id}/finish")
async def finish_import_session(
    session_id: str,
    success: bool = True,
    message: Optional[str] = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Finalizar uma sessão de importação.
    """
    await finish_background_job_db(session_id, success, message)
    
    job = background_processes.get(session_id) or await db.background_jobs.find_one({"id": session_id}, {"_id": 0})
    return job or {"error": "Sessão não encontrada"}


# ====================================================================
# IMPORTAÇÃO AGREGADA - CLIENTE A CLIENTE (P0)
# ====================================================================
# Nova lógica de importação que:
# 1. Acumula dados extraídos de múltiplos documentos por cliente
# 2. Deduplica campos (usa valor mais recente quando há conflito)
# 3. Agrega salários por empresa (lista + soma total)
# 4. Salva uma única vez por cliente após processar todos os documentos
# ====================================================================

class AggregatedSessionRequest(BaseModel):
    """Request para iniciar sessão de importação agregada."""
    total_files: int
    client_id: Optional[str] = None  # Se definido, todos os ficheiros vão para este cliente
    client_name: Optional[str] = None


class AggregatedSessionResponse(BaseModel):
    """Response da sessão de importação agregada."""
    session_id: str
    message: str
    aggregation_mode: bool = True


@router.post("/aggregated-session/start", response_model=AggregatedSessionResponse)
async def start_aggregated_session(
    request: AggregatedSessionRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Iniciar sessão de importação AGREGADA.
    
    Diferente da sessão normal, esta sessão:
    1. Acumula dados extraídos em memória (não salva imediatamente)
    2. Quando finalizada, consolida e deduplica dados
    3. Agrega salários por empresa (lista separada + soma)
    4. Salva uma única vez por cliente
    
    Returns:
        session_id: ID único da sessão para usar nos próximos requests
    """
    # Criar job de background para tracking
    details = {
        "aggregation_mode": True,
        "client_id": request.client_id,
        "client_name": request.client_name
    }
    
    session_id = await create_background_job_db(
        job_type="aggregated_import",
        user_email=user.get("email"),
        details=details,
        total_files=request.total_files
    )
    
    # Criar sessão de agregação em memória
    session = get_or_create_session(session_id, user.get("email"))
    session.total_files = request.total_files
    
    # Persistir na DB para recuperação após reinício
    await persist_session_to_db(session)
    
    logger.info(f"[AGGREGATED] Sessão iniciada: {session_id} com {request.total_files} ficheiros")
    
    return AggregatedSessionResponse(
        session_id=session_id,
        message=f"Sessão agregada iniciada com {request.total_files} ficheiros",
        aggregation_mode=True
    )


class AggregatedFileResult(BaseModel):
    """Resultado do processamento de um ficheiro na sessão agregada."""
    success: bool
    client_name: str
    filename: str
    document_type: str = ""
    fields_extracted: List[str] = []
    aggregated: bool = True  # Indica que os dados foram agregados (não salvos ainda)
    error: Optional[str] = None


@router.post("/aggregated-session/{session_id}/analyze", response_model=AggregatedFileResult)
async def analyze_file_aggregated(
    session_id: str,
    file: UploadFile = File(...),
    force_client_id: Optional[str] = Form(None),
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Analisar ficheiro e AGREGAR dados (não salva ainda).
    
    Os dados extraídos são acumulados na sessão de agregação.
    A consolidação e salvamento só acontece quando a sessão é finalizada.
    
    Args:
        session_id: ID da sessão de importação agregada
        file: Ficheiro a analisar
        force_client_id: ID do cliente para forçar associação (Cenário B)
    """
    # Verificar se sessão existe (primeiro memória, depois DB)
    session = await get_session_async(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão de agregação não encontrada. A sessão pode ter expirado ou o servidor foi reiniciado. Por favor, inicie uma nova importação.")
    
    filename = file.filename or "documento.pdf"
    
    # Extrair nome do cliente do path
    parts = filename.replace("\\", "/").split("/")
    if len(parts) >= 2:
        folder_name = parts[1]
        doc_filename = parts[-1]
    else:
        doc_filename = parts[0]
        folder_name = doc_filename.rsplit("_", 1)[0] if "_" in doc_filename else "Desconhecido"
    
    client_name = folder_name
    
    result = AggregatedFileResult(
        success=False,
        client_name=client_name,
        filename=doc_filename,
        aggregated=True
    )
    
    try:
        # Ler ficheiro
        content = await read_file_with_limit(file)
        
        # Validação de segurança
        try:
            validate_file_content(content, doc_filename)
        except HTTPException as e:
            result.error = f"Ficheiro rejeitado: {e.detail}"
            session.increment_error()
            return result
        
        # Encontrar cliente
        process = None
        process_id = None
        
        if force_client_id:
            process = await db.processes.find_one({"id": force_client_id}, {"_id": 0})
            if process:
                process_id = force_client_id
            else:
                result.error = f"Cliente com ID '{force_client_id}' não encontrado"
                session.increment_error()
                return result
        else:
            # Cache NIF ou busca por nome
            cached_mapping = await get_cached_nif_mapping(folder_name)
            if cached_mapping:
                process_id = cached_mapping["process_id"]
                process = await db.processes.find_one({"id": process_id}, {"_id": 0})
            
            if not process:
                process = await find_client_by_name(client_name)
        
        if not process:
            result.error = f"Cliente não encontrado: {client_name}"
            session.increment_error()
            return result
        
        process_id = process.get("id")
        actual_client_name = process.get("client_name", client_name)
        result.client_name = actual_client_name
        
        # Detectar tipo de documento
        document_type = detect_document_type(doc_filename)
        result.document_type = document_type
        
        # Verificar duplicado
        duplicate_data = await check_duplicate_comprehensive(process_id, document_type, content)
        if duplicate_data:
            result.success = True
            result.error = "Documento idêntico já analisado (ignorado)"
            return result
        
        # Analisar documento com IA
        analysis_result = await analyze_single_document(
            content=content,
            filename=doc_filename,
            client_name=actual_client_name,
            process_id=process_id
        )
        
        if analysis_result.get("success") and analysis_result.get("extracted_data"):
            extracted_data = analysis_result["extracted_data"]
            
            # === AGREGAR DADOS NA SESSÃO (não salva ainda) ===
            session.add_file_extraction(
                process_id=process_id,
                client_name=actual_client_name,
                document_type=document_type,
                extracted_data=extracted_data,
                filename=doc_filename
            )
            
            # Guardar em cache de duplicados
            cache_document_analysis(process_id, document_type, content, extracted_data)
            
            # Persistir registo do documento analisado
            await persist_document_analysis(
                process_id, document_type, content, extracted_data, doc_filename
            )
            
            result.success = True
            result.fields_extracted = list(extracted_data.keys())
            
            logger.info(f"[AGGREGATED] {doc_filename} agregado para '{actual_client_name}': {len(extracted_data)} campos")
        else:
            result.error = analysis_result.get("error", "Erro na análise")
            session.increment_error()
        
    except Exception as e:
        result.error = f"Erro inesperado: {str(e)}"
        session.increment_error()
        logger.error(f"[AGGREGATED] Erro ao processar {filename}: {e}", exc_info=True)
    
    return result


class AggregatedFinishResponse(BaseModel):
    """Response da finalização da sessão agregada."""
    success: bool
    message: str
    clients_updated: int
    total_documents: int
    errors: int
    summary: Dict[str, Any] = {}


@router.post("/aggregated-session/{session_id}/finish", response_model=AggregatedFinishResponse)
async def finish_aggregated_session(
    session_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Finalizar sessão de importação AGREGADA.
    
    Este endpoint:
    1. Consolida todos os dados acumulados por cliente
    2. Deduplica campos (valor mais recente ganha)
    3. Agrega salários por empresa (lista + soma)
    4. Salva uma única vez na DB para cada cliente
    5. Fecha a sessão de agregação
    
    Returns:
        Resumo da importação com dados de cada cliente actualizado
    """
    session = await get_session_async(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão de agregação não encontrada. A sessão pode ter expirado ou o servidor foi reiniciado.")
    
    clients_updated = 0
    errors_count = session.errors
    
    try:
        # Obter dados consolidados de todos os clientes
        all_consolidated = session.get_all_consolidated_data()
        
        for process_id, consolidated_data in all_consolidated.items():
            try:
                # Obter dados existentes do cliente
                existing_process = await db.processes.find_one({"id": process_id}, {"_id": 0})
                if not existing_process:
                    logger.warning(f"[AGGREGATED] Processo não encontrado: {process_id}")
                    continue
                
                # Merge com dados existentes
                update_data = {}
                
                # Personal data - merge
                if consolidated_data.get("personal_data"):
                    existing_personal = existing_process.get("personal_data") or {}
                    existing_personal.update(consolidated_data["personal_data"])
                    update_data["personal_data"] = existing_personal
                
                # Financial data - merge
                if consolidated_data.get("financial_data"):
                    existing_financial = existing_process.get("financial_data") or {}
                    existing_financial.update(consolidated_data["financial_data"])
                    update_data["financial_data"] = existing_financial
                
                # Real estate data - merge
                if consolidated_data.get("real_estate_data"):
                    existing_real_estate = existing_process.get("real_estate_data") or {}
                    existing_real_estate.update(consolidated_data["real_estate_data"])
                    update_data["real_estate_data"] = existing_real_estate
                
                # Co-buyers e co-applicants
                if consolidated_data.get("co_buyers"):
                    update_data["co_buyers"] = consolidated_data["co_buyers"]
                if consolidated_data.get("co_applicants"):
                    update_data["co_applicants"] = consolidated_data["co_applicants"]
                
                # Metadata da importação
                update_data["updated_at"] = consolidated_data.get("updated_at")
                update_data["ai_import_aggregated"] = True
                update_data["ai_import_timestamp"] = consolidated_data.get("ai_import_timestamp")
                update_data["ai_documents_count"] = consolidated_data.get("ai_documents_count", 0)
                
                # Histórico de extracções
                if consolidated_data.get("ai_extraction_history"):
                    update_data["$push"] = {
                        "ai_extraction_history": {
                            "$each": consolidated_data["ai_extraction_history"]
                        }
                    }
                    # Separar $push do $set
                    push_data = update_data.pop("$push")
                    
                    # Aplicar actualização
                    await db.processes.update_one(
                        {"id": process_id},
                        {"$set": update_data, "$push": push_data}
                    )
                else:
                    await db.processes.update_one(
                        {"id": process_id},
                        {"$set": update_data}
                    )
                
                clients_updated += 1
                client_name = existing_process.get("client_name", process_id)
                logger.info(f"[AGGREGATED] Cliente '{client_name}' actualizado com dados agregados")
                
            except Exception as e:
                errors_count += 1
                logger.error(f"[AGGREGATED] Erro ao actualizar {process_id}: {e}")
        
        # Obter resumo da sessão
        summary = session.get_session_summary()
        
        # Finalizar job de background
        await finish_background_job_db(
            session_id,
            success=clients_updated > 0,
            message=f"{clients_updated} clientes actualizados, {session.processed_files} documentos processados"
        )
        
        # Fechar e remover sessão de memória
        close_session(session_id)
        
        return AggregatedFinishResponse(
            success=clients_updated > 0,
            message=f"Importação agregada concluída: {clients_updated} clientes actualizados",
            clients_updated=clients_updated,
            total_documents=session.processed_files,
            errors=errors_count,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"[AGGREGATED] Erro ao finalizar sessão {session_id}: {e}", exc_info=True)
        close_session(session_id)
        raise HTTPException(status_code=500, detail=f"Erro ao finalizar importação: {str(e)}")


@router.get("/aggregated-session/{session_id}/status")
async def get_aggregated_session_status(
    session_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Obter estado da sessão de importação agregada."""
    session = await get_session_async(session_id)
    if not session:
        # Tentar buscar da DB
        job = await db.background_jobs.find_one({"id": session_id}, {"_id": 0})
        if job:
            return {
                "session_id": session_id,
                "status": job.get("status", "unknown"),
                "from_db": True,
                **job
            }
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return {
        "session_id": session_id,
        "status": "active",
        "in_memory": True,
        **session.get_session_summary()
    }


# ====================================================================
# ACTUALIZAÇÃO DE PROGRESSO DO BACKGROUND JOB
# ====================================================================
class ProgressUpdateRequest(BaseModel):
    """Request para actualizar progresso de um job."""
    processed: Optional[int] = None
    errors: Optional[int] = None
    message: Optional[str] = None


@router.post("/background-job/{job_id}/progress")
async def update_background_job_progress(
    job_id: str,
    request: ProgressUpdateRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Actualizar progresso de um job em background.
    
    Usado pelo frontend para reportar progresso de uploads.
    Actualiza tanto o cache em memória como a DB.
    """
    update_fields = {}
    
    if request.processed is not None:
        update_fields["processed"] = request.processed
    if request.errors is not None:
        update_fields["errors"] = request.errors
    if request.message:
        update_fields["message"] = request.message
    
    if update_fields:
        await update_background_job_db(job_id, **update_fields)
    
    # Retornar estado actual
    job = background_processes.get(job_id)
    if not job:
        job = await db.background_jobs.find_one({"id": job_id}, {"_id": 0})
    
    return job or {"error": "Job não encontrado", "updated": bool(update_fields)}


@router.post("/analyze-single", response_model=SingleAnalysisResult)
async def analyze_single_file(
    file: UploadFile = File(...),
    force_client_id: Optional[str] = Form(None),
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
    - NOVO (Item 17): Cache de sessão NIF - mapeamento pasta → cliente
    - NOVO: Parâmetro force_client_id para forçar associação a um cliente específico
    
    Args:
        file: Ficheiro a analisar
        force_client_id: ID do processo/cliente para associar forçadamente (opcional)
                        Se fornecido, ignora a detecção automática de cliente
    
    Estrutura do path: PastaRaiz/NomeCliente/[subpastas/]documento.pdf
    """
    filename = file.filename or "documento.pdf"
    
    # Limpar cache NIF expirado periodicamente
    await clear_expired_nif_cache()
    
    # Extrair nome do cliente (pasta) do path
    parts = filename.replace("\\", "/").split("/")
    
    if len(parts) >= 2:
        folder_name = parts[1]  # Nome da pasta = nome do cliente
        doc_filename = parts[-1]
    else:
        doc_filename = parts[0]
        if "_" in doc_filename:
            folder_name = doc_filename.rsplit("_", 1)[0]
        else:
            folder_name = "Desconhecido"
    
    # Usar folder_name como client_name inicial
    client_name = folder_name
    
    result = SingleAnalysisResult(
        success=False,
        client_name=client_name,
        filename=doc_filename
    )
    
    try:
        # Ler ficheiro imediatamente
        content = await read_file_with_limit(file)
        
        # ================================================================
        # VALIDAÇÃO DE SEGURANÇA - Magic Bytes
        # Verifica se o conteúdo real corresponde a um tipo permitido
        # ================================================================
        try:
            validate_file_content(content, doc_filename)
        except HTTPException as security_error:
            logger.warning(f"[SECURITY] Ficheiro rejeitado: {filename} - {security_error.detail}")
            result.error = f"Ficheiro rejeitado: {security_error.detail}"
            return result
        
        mime_type = get_mime_type(doc_filename)
        
        # ================================================================
        # FORCE CLIENT ID - Se fornecido, usar directamente
        # ================================================================
        process = None
        process_id = None
        
        if force_client_id:
            # Usar o ID do cliente fornecido directamente
            process = await db.processes.find_one({"id": force_client_id}, {"_id": 0})
            if process:
                process_id = force_client_id
                logger.info(f"[FORCE_CLIENT_ID] Usando cliente forçado: {force_client_id}")
            else:
                result.error = f"Cliente com ID '{force_client_id}' não encontrado."
                logger.warning(f"force_client_id inválido: {force_client_id}")
                return result
        else:
            # ================================================================
            # CACHE DE SESSÃO NIF (Item 17)
            # Verificar se já temos mapeamento pasta → cliente em cache
            # ================================================================
            cached_mapping = await get_cached_nif_mapping(folder_name)
            
            if cached_mapping:
                # Usar mapeamento em cache (muito mais rápido)
                process_id = cached_mapping["process_id"]
                process = await db.processes.find_one({"id": process_id}, {"_id": 0})
                if process:
                    logger.info(f"[NIF CACHE] Usando mapeamento em cache para '{folder_name}' -> '{cached_mapping['client_name']}'")
            
            # Se não encontrou em cache, procurar por nome
            if not process:
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
                        
                        # Limpar cache CC
                        del cc_cache[process_id]
                        
                        if analysis_result.get("success") or analysis_result.get("extracted_data"):
                            result.success = True
                            result.fields_extracted = list(analysis_result.get("extracted_data", {}).keys())
                            result.filename = normalized_name
                            
                            # ================================================================
                            # CACHE DE SESSÃO NIF (Item 17)
                            # Se o CC extraiu NIF, guardar mapeamento pasta → cliente
                            # ================================================================
                            extracted_data = analysis_result.get("extracted_data", {})
                            extracted_nif = extracted_data.get("nif")
                            if extracted_nif:
                                await cache_nif_mapping(
                                    folder_name=folder_name,
                                    nif=extracted_nif,
                                    process_id=process_id,
                                    client_name=actual_client_name
                                )
                            
                            # Persistir análise do CC na DB
                            await persist_document_analysis(
                                process_id,
                                "cc",
                                merged_pdf,
                                extracted_data,
                                "CC_frente_verso.pdf"
                            )
                            
                            # Actualizar ficha do cliente
                            updated, fields, conflicts = await update_client_data(
                                process_id,
                                extracted_data,
                                document_type
                            )
                            result.updated = updated
                            if conflicts:
                                result.conflicts = conflicts
                            
                            # Registar sucesso no log de importação
                            await log_import_result(
                                client_name=actual_client_name,
                                process_id=process_id,
                                filename="CC_frente_verso.pdf",
                                document_type="cc",
                                success=True,
                                extracted_data=extracted_data,
                                updated_fields=fields,
                                user_email=user.get("email"),
                                folder_name=folder_name,
                                full_path=filename
                            )
                            
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
            
            extracted_data = analysis_result["extracted_data"]
            
            # ================================================================
            # CACHE DE SESSÃO NIF (Item 17)
            # Se for CC e extraiu NIF, guardar mapeamento pasta → cliente
            # ================================================================
            if document_type == "cc":
                extracted_nif = extracted_data.get("nif")
                if extracted_nif:
                    await cache_nif_mapping(
                        folder_name=folder_name,
                        nif=extracted_nif,
                        process_id=process_id,
                        client_name=actual_client_name
                    )
            
            # Guardar em cache (memória) para detectar duplicados durante a sessão
            cache_document_analysis(process_id, document_type, content, extracted_data)
            
            # Persistir na DB para detectar duplicados após reinício
            await persist_document_analysis(
                process_id, 
                document_type, 
                content, 
                extracted_data,
                doc_filename
            )
            
            # Actualizar ficha do cliente
            updated, fields, conflicts = await update_client_data(
                process_id,
                extracted_data,
                document_type
            )
            result.updated = updated
            if conflicts:
                result.conflicts = conflicts
            
            # Registar sucesso no log de importação
            await log_import_result(
                client_name=actual_client_name,
                process_id=process_id,
                filename=doc_filename,
                document_type=document_type,
                success=True,
                extracted_data=extracted_data,
                updated_fields=fields,
                user_email=user.get("email"),
                folder_name=folder_name,
                full_path=filename
            )
            
            logger.info(f"✅ {doc_filename} -> {normalized_name} para '{actual_client_name}': {len(result.fields_extracted)} campos extraídos, {len(fields)} actualizados")
        else:
            result.error = analysis_result.get("error", "Erro na análise")
            logger.warning(f"❌ Falha ao analisar {doc_filename}: {result.error}")
            
            # Guardar erro no log de importação
            await log_import_error(
                client_name=actual_client_name,
                process_id=process_id,
                filename=doc_filename,
                document_type=document_type,
                error=result.error,
                user_email=user.get("email")
            )
        
    except ValueError as e:
        result.error = str(e)
        await log_import_error(
            client_name=client_name,
            process_id=process_id if 'process_id' in dir() else None,
            filename=doc_filename,
            document_type=document_type if 'document_type' in dir() else "desconhecido",
            error=str(e),
            user_email=user.get("email")
        )
    except Exception as e:
        result.error = f"Erro inesperado: {str(e)}"
        logger.error(f"Erro ao processar {filename}: {e}", exc_info=True)
        await log_import_error(
            client_name=client_name,
            process_id=process_id if 'process_id' in dir() else None,
            filename=doc_filename,
            document_type=document_type if 'document_type' in dir() else "desconhecido",
            error=str(e),
            user_email=user.get("email")
        )
    
    return result


def categorize_extracted_fields(extracted_data: dict, document_type: str) -> Dict[str, Dict[str, Any]]:
    """
    Categorizar campos extraídos em: dados_pessoais, imovel, financiamento, outros.
    Baseado na estrutura da ficha de cliente.
    """
    categories = {
        "dados_pessoais": {},
        "imovel": {},
        "financiamento": {},
        "outros": {}
    }
    
    # Mapeamento de campos para categorias
    personal_fields = [
        "nome", "name", "nif", "NIF", "data_nascimento", "morada", "codigo_postal",
        "localidade", "telefone", "email", "estado_civil", "nacionalidade",
        "cc_numero", "cc_validade", "genero", "profissao", "entidade_empregadora",
        "tipo_contrato", "antiguidade", "rendimento_mensal", "outros_rendimentos"
    ]
    
    property_fields = [
        "tipo_imovel", "finalidade", "valor_imovel", "valor_escritura",
        "morada_imovel", "distrito", "concelho", "freguesia", "ano_construcao",
        "area_bruta", "area_util", "tipologia", "caderneta_predial", "artigo"
    ]
    
    finance_fields = [
        "valor_financiamento", "prazo", "taxa_esforco", "spread", "euribor",
        "prestacao", "lti", "ltv", "banco", "entidade_bancaria",
        "despesas_mensais", "encargos", "creditos_existentes"
    ]
    
    for key, value in extracted_data.items():
        if value is None or value == "":
            continue
            
        key_lower = key.lower()
        
        if key_lower in [f.lower() for f in personal_fields] or key_lower.startswith("personal"):
            categories["dados_pessoais"][key] = value
        elif key_lower in [f.lower() for f in property_fields] or key_lower.startswith("property") or key_lower.startswith("imovel"):
            categories["imovel"][key] = value
        elif key_lower in [f.lower() for f in finance_fields] or key_lower.startswith("financ"):
            categories["financiamento"][key] = value
        else:
            categories["outros"][key] = value
    
    # Remover categorias vazias
    return {k: v for k, v in categories.items() if v}


async def log_import_result(
    client_name: str,
    process_id: Optional[str],
    filename: str,
    document_type: str,
    success: bool,
    extracted_data: Optional[dict] = None,
    updated_fields: Optional[List[str]] = None,
    error: Optional[str] = None,
    user_email: str = None,
    folder_name: str = None,
    full_path: str = None
):
    """
    Registar resultado de importação (sucesso ou erro) na base de dados.
    Organiza os dados por categorias para visualização em tabs.
    """
    try:
        log_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Categorizar dados extraídos
        categorized_data = {}
        if extracted_data:
            categorized_data = categorize_extracted_fields(extracted_data, document_type)
        
        # Construir log completo
        import_log = {
            "id": log_id,
            "timestamp": timestamp,
            "status": "success" if success else "error",
            "client_name": client_name,
            "process_id": process_id,
            "filename": filename,
            "document_type": document_type,
            "folder_name": folder_name or client_name,
            "full_path": full_path or filename,
            "user_email": user_email,
            # Dados categorizados para visualização em tabs
            "categorized_data": categorized_data,
            "updated_fields": updated_fields or [],
            "fields_count": len(updated_fields) if updated_fields else 0,
            "error": error,
            "resolved": success,  # Sucessos já estão "resolvidos"
        }
        
        # Guardar na nova colecção de logs de importação
        await db.ai_import_logs.insert_one(import_log)
        
        # Se for erro, também guardar na colecção de erros (compatibilidade)
        if not success and error:
            error_log = {
                "id": log_id,
                "timestamp": timestamp,
                "client_name": client_name,
                "process_id": process_id,
                "filename": filename,
                "document_type": document_type,
                "error": error,
                "user_email": user_email,
                "resolved": False,
                "folder_name": folder_name or client_name,
                "full_path": full_path or filename,
            }
            await db.import_errors.insert_one(error_log)
        
        log_status = "✅ Sucesso" if success else "❌ Erro"
        logger.info(f"Log de importação registado: {log_status} - {filename} -> {client_name}")
        
    except Exception as e:
        logger.error(f"Falha ao registar log de importação: {e}")


async def log_import_error(
    client_name: str,
    process_id: Optional[str],
    filename: str,
    document_type: str,
    error: str,
    user_email: str = None,
    # Novos campos (Item 15)
    folder_name: str = None,
    attempted_matches: List[str] = None,
    best_match_score: int = None,
    best_match_name: str = None,
    extracted_names: List[str] = None,
    full_path: str = None
):
    """
    Guardar erro de importação na base de dados para análise posterior.
    Usa a nova função log_import_result para consistência.
    """
    await log_import_result(
        client_name=client_name,
        process_id=process_id,
        filename=filename,
        document_type=document_type,
        success=False,
        error=error,
        user_email=user_email,
        folder_name=folder_name,
        full_path=full_path
    )
    
    # Também registar nos logs do sistema para visualização unificada
    try:
        error_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        error_details = {
            "client_name": client_name,
            "process_id": process_id,
            "filename": filename,
            "document_type": document_type,
            "folder_name": folder_name or client_name,
            "full_path": full_path or filename,
            "user_email": user_email
        }
        
        if any([attempted_matches, best_match_score, extracted_names]):
            error_details["matching_details"] = {
                "attempted_matches": attempted_matches[:10] if attempted_matches else [],
                "best_match_score": best_match_score,
                "best_match_name": best_match_name,
                "extracted_names": list(extracted_names)[:5] if extracted_names else []
            }
        
        system_log = {
            "id": error_id,
            "timestamp": timestamp,
            "severity": "warning",
            "component": "import",
            "error_type": "import_error",
            "message": f"Erro de importação: {error}",
            "details": error_details,
            "resolved": False,
            "context": {
                "filename": filename,
                "client": client_name,
                "user": user_email
            }
        }
        await db.system_error_logs.insert_one(system_log)
        
    except Exception as e:
        logger.error(f"Falha ao registar erro no system_error_logs: {e}")


# ====================================================================
# ENDPOINT PARA PROCESSOS EM BACKGROUND (Item 2)
# ====================================================================
@router.get("/background-jobs")
async def get_background_jobs(
    status: Optional[str] = None,
    limit: int = 20,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Listar processos em background (Item 2 - Outros erros/melhorias).
    
    Parâmetros:
    - status: Filtrar por estado (running, success, failed)
    - limit: Número máximo de resultados (default 20)
    
    Returns:
        Lista de jobs com estado, progresso e detalhes
    """
    # Carregar jobs recentes da DB (última semana)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    query = {"started_at": {"$gte": cutoff}}
    
    if status:
        query["status"] = status
    
    # Buscar da DB
    db_jobs = await db.background_jobs.find(
        query,
        {"_id": 0}
    ).sort("started_at", -1).limit(limit).to_list(limit)
    
    # Juntar com jobs em memória (podem existir jobs novos ainda não na DB)
    all_jobs = {job["id"]: job for job in db_jobs}
    for job_id, job in background_processes.items():
        if job_id not in all_jobs:
            if not status or job.get("status") == status:
                all_jobs[job_id] = job
    
    jobs = list(all_jobs.values())
    jobs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    jobs = jobs[:limit]
    
    # Contar por status (da DB para precisão)
    running_count = await db.background_jobs.count_documents({"status": "running"})
    paused_count = await db.background_jobs.count_documents({"status": "paused"})
    success_count = await db.background_jobs.count_documents({"status": "success", "started_at": {"$gte": cutoff}})
    failed_count = await db.background_jobs.count_documents({"status": "failed", "started_at": {"$gte": cutoff}})
    total_count = await db.background_jobs.count_documents({"started_at": {"$gte": cutoff}})
    
    counts = {
        "running": running_count,
        "paused": paused_count,
        "success": success_count,
        "failed": failed_count,
        "total": total_count
    }
    
    return {
        "jobs": jobs,
        "counts": counts
    }


@router.get("/background-jobs/{job_id}")
async def get_background_job_status(
    job_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Obter estado de um job específico.
    """
    # Tentar memória primeiro (mais rápido)
    if job_id in background_processes:
        return background_processes[job_id]
    
    # Buscar na DB
    job = await db.background_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return job


@router.delete("/background-jobs/{job_id}")
async def delete_background_job(
    job_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Remover um job do histórico.
    Nota: Não interrompe processos já em execução.
    """
    # Remover da memória
    job = background_processes.pop(job_id, None)
    
    # Remover da DB
    result = await db.background_jobs.delete_one({"id": job_id})
    
    if not job and result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return {
        "success": True,
        "message": f"Job {job_id} removido",
        "job": job
    }


@router.post("/background-jobs/{job_id}/cancel")
async def cancel_background_job(
    job_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Cancelar um job em execução.
    
    Marca o job como 'cancelled' e actualiza a DB.
    Os processos já em execução não podem ser interrompidos,
    mas ficheiros pendentes serão ignorados.
    """
    # Verificar se existe na memória
    job = background_processes.get(job_id)
    
    if not job:
        # Tentar encontrar na DB
        job = await db.background_jobs.find_one({"id": job_id}, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    if job.get("status") != "running":
        raise HTTPException(status_code=400, detail="Apenas jobs em execução podem ser cancelados")
    
    # Marcar como cancelado
    update_data = {
        "status": "cancelled",
        "message": "Cancelado pelo utilizador",
        "finished_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Actualizar na memória
    if job_id in background_processes:
        background_processes[job_id].update(update_data)
    
    # Actualizar na DB
    await db.background_jobs.update_one(
        {"id": job_id},
        {"$set": update_data}
    )
    
    return {
        "success": True,
        "message": f"Job {job_id} cancelado",
        "status": "cancelled"
    }


@router.post("/background-jobs/{job_id}/pause")
async def pause_background_job(
    job_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Pausar um job em execução.
    
    Marca o job como 'paused' e os ficheiros pendentes não serão processados
    até o job ser retomado.
    """
    # Verificar se existe na memória
    job = background_processes.get(job_id)
    
    if not job:
        # Tentar encontrar na DB
        job = await db.background_jobs.find_one({"id": job_id}, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    if job.get("status") != "running":
        raise HTTPException(status_code=400, detail="Apenas jobs em execução podem ser pausados")
    
    # Marcar como pausado
    update_data = {
        "status": "paused",
        "paused_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Actualizar na memória
    if job_id in background_processes:
        background_processes[job_id].update(update_data)
    
    # Actualizar na DB
    await db.background_jobs.update_one(
        {"id": job_id},
        {"$set": update_data}
    )
    
    return {
        "success": True,
        "message": f"Job {job_id} pausado",
        "status": "paused"
    }


@router.post("/background-jobs/{job_id}/resume")
async def resume_background_job(
    job_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Retomar um job pausado.
    
    Marca o job como 'running' novamente para continuar o processamento.
    """
    # Verificar se existe na memória
    job = background_processes.get(job_id)
    
    if not job:
        # Tentar encontrar na DB
        job = await db.background_jobs.find_one({"id": job_id}, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    if job.get("status") != "paused":
        raise HTTPException(status_code=400, detail="Apenas jobs pausados podem ser retomados")
    
    # Marcar como running novamente
    update_data = {
        "status": "running",
        "resumed_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Actualizar na memória
    if job_id in background_processes:
        background_processes[job_id].update(update_data)
    
    # Actualizar na DB
    await db.background_jobs.update_one(
        {"id": job_id},
        {"$set": update_data}
    )
    
    return {
        "success": True,
        "message": f"Job {job_id} retomado",
        "status": "running"
    }


@router.delete("/background-jobs")
async def clear_finished_jobs(
    only_failed: bool = False,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Limpar jobs terminados do histórico.
    
    Parâmetros:
    - only_failed: Se True, limpa apenas jobs falhados (default False)
    """
    # Remover da memória
    to_remove = []
    for job_id, job in background_processes.items():
        status = job.get("status")
        if status != "running":
            if only_failed:
                if status == "failed":
                    to_remove.append(job_id)
            else:
                to_remove.append(job_id)
    
    for job_id in to_remove:
        del background_processes[job_id]
    
    # Remover da DB
    query = {"status": {"$ne": "running"}}
    if only_failed:
        query["status"] = "failed"
    
    db_result = await db.background_jobs.delete_many(query)
    
    return {
        "success": True,
        "removed_count": db_result.deleted_count,
        "message": f"{db_result.deleted_count} jobs removidos"
    }


@router.post("/background-jobs/clear-all")
async def clear_all_jobs(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Limpar TODOS os jobs do histórico (incluindo running).
    Útil para limpar jobs stuck.
    """
    # Limpar da memória
    count_memory = len(background_processes)
    background_processes.clear()
    
    # Limpar da DB
    db_result = await db.background_jobs.delete_many({})
    
    return {
        "success": True,
        "removed_memory": count_memory,
        "removed_db": db_result.deleted_count,
        "message": f"Removidos {count_memory} jobs da memória e {db_result.deleted_count} da DB"
    }


@router.get("/import-errors")
async def get_import_errors(
    limit: int = 100,
    document_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Obter lista de erros de importação para análise.
    
    Parâmetros:
    - limit: Número máximo de erros a retornar (default 100)
    - document_type: Filtrar por tipo de documento
    - resolved: Filtrar por estado (True=resolvidos, False=pendentes)
    """
    query = {}
    
    if document_type:
        query["document_type"] = document_type
    if resolved is not None:
        query["resolved"] = resolved
    
    errors = await db.import_errors.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).to_list(length=limit)
    
    # Agrupar por tipo de erro para análise
    error_summary = {}
    for err in errors:
        error_key = err.get("error", "Desconhecido")[:100]  # Truncar para agrupar
        if error_key not in error_summary:
            error_summary[error_key] = {
                "count": 0,
                "document_types": set(),
                "clients": set()
            }
        error_summary[error_key]["count"] += 1
        error_summary[error_key]["document_types"].add(err.get("document_type", "?"))
        error_summary[error_key]["clients"].add(err.get("client_name", "?"))
    
    # Converter sets para listas
    for key in error_summary:
        error_summary[key]["document_types"] = list(error_summary[key]["document_types"])
        error_summary[key]["clients"] = list(error_summary[key]["clients"])[:5]  # Limitar a 5 exemplos
    
    return {
        "total_errors": len(errors),
        "errors": errors,
        "summary": error_summary
    }


@router.get("/import-errors/summary")
async def get_import_errors_summary(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Obter resumo estatístico dos erros de importação.
    Útil para identificar padrões e áreas de melhoria.
    """
    # Agregação por tipo de documento
    pipeline_by_type = [
        {"$group": {"_id": "$document_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    # Agregação por erro (primeiros 50 caracteres)
    pipeline_by_error = [
        {"$project": {
            "error_prefix": {"$substr": ["$error", 0, 80]},
            "document_type": 1
        }},
        {"$group": {"_id": "$error_prefix", "count": {"$sum": 1}, "types": {"$addToSet": "$document_type"}}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    
    # Agregação temporal (últimas 24h, 7 dias, 30 dias)
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    errors_24h = await db.import_errors.count_documents({
        "timestamp": {"$gte": (now - timedelta(hours=24)).isoformat()}
    })
    errors_7d = await db.import_errors.count_documents({
        "timestamp": {"$gte": (now - timedelta(days=7)).isoformat()}
    })
    errors_30d = await db.import_errors.count_documents({
        "timestamp": {"$gte": (now - timedelta(days=30)).isoformat()}
    })
    total_errors = await db.import_errors.count_documents({})
    unresolved = await db.import_errors.count_documents({"resolved": False})
    
    by_type_cursor = db.import_errors.aggregate(pipeline_by_type)
    by_type = [doc async for doc in by_type_cursor]
    
    by_error_cursor = db.import_errors.aggregate(pipeline_by_error)
    by_error = [doc async for doc in by_error_cursor]
    
    return {
        "total_errors": total_errors,
        "unresolved": unresolved,
        "temporal": {
            "last_24h": errors_24h,
            "last_7d": errors_7d,
            "last_30d": errors_30d
        },
        "by_document_type": [{"type": d["_id"], "count": d["count"]} for d in by_type],
        "top_errors": [{"error": d["_id"], "count": d["count"], "types": d["types"]} for d in by_error]
    }


@router.post("/import-errors/{error_id}/resolve")
async def resolve_import_error(
    error_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Marcar um erro de importação como resolvido."""
    result = await db.import_errors.update_one(
        {"id": error_id},
        {"$set": {"resolved": True, "resolved_by": user.get("email"), "resolved_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count > 0:
        return {"success": True, "message": "Erro marcado como resolvido"}
    else:
        return {"success": False, "message": "Erro não encontrado"}


@router.delete("/import-errors/clear")
async def clear_import_errors(
    older_than_days: int = 30,
    only_resolved: bool = True,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Limpar erros de importação antigos.
    
    Parâmetros:
    - older_than_days: Limpar erros mais antigos que X dias (default 30)
    - only_resolved: Se True, limpa apenas erros resolvidos (default True)
    """
    from datetime import timedelta
    
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
    
    query = {"timestamp": {"$lt": cutoff_date}}
    if only_resolved:
        query["resolved"] = True
    
    result = await db.import_errors.delete_many(query)
    
    return {
        "success": True,
        "deleted_count": result.deleted_count,
        "message": f"{result.deleted_count} erros removidos (anteriores a {older_than_days} dias)"
    }


@router.get("/suggest-clients")
async def suggest_clients(
    query: str,
    limit: int = 5,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Retornar clientes similares para selecção manual (Item 14).
    Usado quando o matching automático falha.
    
    Parâmetros:
    - query: Nome/termo a pesquisar
    - limit: Número máximo de sugestões (default 5, max 10)
    
    Returns:
        Lista de sugestões com nome, id, score e contagem de documentos
    """
    if not query or len(query) < 2:
        return {
            "query": query,
            "suggestions": [],
            "message": "Query deve ter pelo menos 2 caracteres"
        }
    
    # Limitar resultados
    limit = min(limit, 10)
    
    # Importar fuzzywuzzy
    try:
        from fuzzywuzzy import fuzz
        HAS_FUZZY = True
    except ImportError:
        HAS_FUZZY = False
    
    # Normalizar query
    query_normalized = normalize_text_for_matching(query)
    query_names = extract_all_names_from_string(query)
    
    # Buscar todos os clientes
    all_processes = await db.processes.find(
        {},
        {"_id": 0, "id": 1, "client_name": 1, "process_number": 1, "analyzed_documents": 1}
    ).to_list(length=None)
    
    # Calcular scores
    scored_results = []
    
    for proc in all_processes:
        proc_name = proc.get("client_name", "")
        if not proc_name:
            continue
        
        proc_name_normalized = normalize_text_for_matching(proc_name)
        
        # Calcular score
        if HAS_FUZZY:
            # Usar token_set_ratio para melhor matching de nomes
            score = fuzz.token_set_ratio(query_normalized, proc_name_normalized)
        else:
            # Fallback: matching simples
            if query_normalized in proc_name_normalized:
                score = 80
            elif proc_name_normalized in query_normalized:
                score = 70
            else:
                # Calcular overlap de palavras
                proc_names = extract_all_names_from_string(proc_name)
                common = query_names & proc_names
                score = len(common) * 25 if common else 0
        
        # Só incluir se score > 30
        if score > 30:
            docs_count = len(proc.get("analyzed_documents", []))
            scored_results.append({
                "name": proc_name,
                "id": proc.get("id"),
                "process_number": proc.get("process_number"),
                "score": score,
                "docs": docs_count
            })
    
    # Ordenar por score (maior primeiro) e limitar
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    suggestions = scored_results[:limit]
    
    return {
        "query": query,
        "total_matches": len(scored_results),
        "suggestions": suggestions
    }


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
    Inclui co-compradores/co-proponentes se existirem.
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
    
    # Verificar co-compradores/co-proponentes
    co_buyers = process.get("co_buyers", [])
    co_applicants = process.get("co_applicants", [])
    
    result = {
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
        },
        "analyzed_documents": process.get("analyzed_documents", [])
    }
    
    # Adicionar co-compradores se existirem
    if co_buyers:
        result["co_buyers"] = co_buyers
        result["summary"]["co_buyers"] = f"{len(co_buyers)} pessoa(s)"
    
    if co_applicants:
        result["co_applicants"] = co_applicants
        result["summary"]["co_applicants"] = f"{len(co_applicants)} pessoa(s)"
    
    return result


@router.get("/analyzed-documents/{process_id}")
async def get_analyzed_documents(
    process_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Listar documentos já analisados para um processo.
    Útil para verificar quais documentos não precisam ser re-analisados.
    """
    process = await db.processes.find_one(
        {"id": process_id},
        {"_id": 0, "client_name": 1, "analyzed_documents": 1}
    )
    
    if not process:
        return {"found": False, "error": "Processo não encontrado"}
    
    analyzed_docs = process.get("analyzed_documents", [])
    
    # Agrupar por tipo de documento
    by_type = {}
    for doc in analyzed_docs:
        doc_type = doc.get("document_type", "outro")
        if doc_type not in by_type:
            by_type[doc_type] = []
        by_type[doc_type].append({
            "filename": doc.get("filename"),
            "analyzed_at": doc.get("analyzed_at"),
            "mes_referencia": doc.get("mes_referencia"),
            "fields_extracted": len(doc.get("fields_extracted", []))
        })
    
    return {
        "found": True,
        "client_name": process.get("client_name"),
        "total_documents": len(analyzed_docs),
        "by_type": by_type
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


@router.get("/nif-cache/stats")
async def get_nif_cache_stats(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Obter estatísticas do cache de sessão NIF.
    
    Mostra quantos mapeamentos pasta→cliente estão em cache (memória e DB).
    """
    # Carregar da DB se ainda não foi feito
    await _load_nif_cache_from_db()
    
    now = datetime.now(timezone.utc)
    
    # Também contar na DB para comparação
    db_count = await db.nif_mappings.count_documents({})
    
    stats = {
        "total_entries_memory": len(nif_session_cache),
        "total_entries_db": db_count,
        "ttl_days": NIF_CACHE_TTL_SECONDS // 86400,
        "entries": []
    }
    
    for folder_key, cached in nif_session_cache.items():
        matched_at = cached.get("matched_at")
        if isinstance(matched_at, str):
            matched_at = datetime.fromisoformat(matched_at.replace("Z", "+00:00"))
        
        age_seconds = (now - matched_at).total_seconds() if matched_at else 0
        
        stats["entries"].append({
            "folder": folder_key,
            "nif": cached.get("nif"),
            "client_name": cached.get("client_name"),
            "age_days": round(age_seconds / 86400, 1),
            "expires_in_days": max(0, round((NIF_CACHE_TTL_SECONDS - age_seconds) / 86400, 1))
        })
    
    return stats


@router.post("/nif-cache/clear")
async def clear_nif_cache(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Limpar todo o cache de sessão NIF (memória e DB)."""
    global nif_session_cache, _nif_cache_loaded
    
    memory_count = len(nif_session_cache)
    nif_session_cache = {}
    _nif_cache_loaded = False
    
    # Limpar também da DB
    db_result = await db.nif_mappings.delete_many({})
    db_count = db_result.deleted_count
    
    logger.info(f"[NIF CACHE] Cache limpo manualmente. Memória: {memory_count}, DB: {db_count}")
    return {
        "message": f"Cache NIF limpo. {memory_count} mapeamentos removidos da memória, {db_count} da base de dados."
    }


@router.post("/nif-cache/add-mapping")
async def add_nif_mapping_manual(
    folder_name: str,
    nif: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Adicionar mapeamento NIF → Cliente manualmente.
    
    Útil quando se sabe o NIF mas a IA não conseguiu extrair automaticamente.
    """
    # Procurar cliente pelo NIF
    process = await find_client_by_nif(nif)
    
    if not process:
        # Tentar encontrar por nome da pasta
        process = await find_client_by_name(folder_name)
        
        if process:
            # Actualizar o NIF na ficha do cliente
            await db.processes.update_one(
                {"id": process["id"]},
                {"$set": {"personal_data.nif": nif, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            logger.info(f"[NIF] NIF {nif} adicionado ao cliente '{process.get('client_name')}'")
        else:
            return {
                "success": False,
                "error": f"Nenhum cliente encontrado com NIF {nif} ou nome '{folder_name}'"
            }
    
    # Guardar mapeamento em cache (e na DB)
    await cache_nif_mapping(
        folder_name=folder_name,
        nif=nif,
        process_id=process["id"],
        client_name=process.get("client_name")
    )
    
    return {
        "success": True,
        "message": f"Mapeamento adicionado: '{folder_name}' -> NIF {nif} -> '{process.get('client_name')}'"
    }


@router.get("/import-errors/suggestions")
async def get_import_improvement_suggestions(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Analisar padrões de erros de importação e gerar sugestões de melhoria.
    
    Este endpoint examina os erros registados e identifica:
    - Padrões comuns de erro
    - Tipos de documentos problemáticos
    - Sugestões específicas para reduzir erros futuros
    """
    from datetime import timedelta
    
    # Obter estatísticas dos erros
    total_errors = await db.import_errors.count_documents({})
    
    if total_errors == 0:
        return {
            "total_errors": 0,
            "suggestions": [
                {
                    "category": "info",
                    "title": "Sem erros registados",
                    "description": "Não há erros de importação para analisar. Continue com as boas práticas actuais!",
                    "priority": "low"
                }
            ],
            "patterns": []
        }
    
    # Agregação por fonte de erro
    pipeline_sources = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    sources_cursor = db.import_errors.aggregate(pipeline_sources)
    sources = [doc async for doc in sources_cursor]
    
    # Agregação por padrão de erro (primeiros 100 chars)
    pipeline_patterns = [
        {"$project": {
            "error_pattern": {"$substr": ["$error_message", 0, 100]},
            "source": 1
        }},
        {"$group": {
            "_id": "$error_pattern",
            "count": {"$sum": 1},
            "sources": {"$addToSet": "$source"}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    patterns_cursor = db.import_errors.aggregate(pipeline_patterns)
    patterns = [doc async for doc in patterns_cursor]
    
    # Gerar sugestões baseadas nos padrões
    suggestions = []
    
    # Analisar padrões específicos e gerar sugestões
    for pattern in patterns:
        error_text = pattern["_id"].lower() if pattern["_id"] else ""
        count = pattern["count"]
        
        # Padrão: Título/campos obrigatórios em falta
        if any(word in error_text for word in ["falta", "obrigatório", "obrigatorio", "required", "missing"]):
            suggestions.append({
                "category": "validation",
                "title": "Campos obrigatórios em falta",
                "description": f"Detectados {count} erros de campos obrigatórios em falta. Verifique se os ficheiros Excel têm todas as colunas necessárias antes de importar.",
                "action": "Criar um template Excel padrão com todos os campos obrigatórios destacados.",
                "priority": "high" if count > 5 else "medium"
            })
        
        # Padrão: Erros de formato/tipo de dados
        elif any(word in error_text for word in ["formato", "format", "tipo", "type", "invalid", "inválido"]):
            suggestions.append({
                "category": "format",
                "title": "Erros de formato de dados",
                "description": f"Detectados {count} erros de formato. Dados podem estar no formato errado (ex: texto em campos numéricos).",
                "action": "Validar formatos antes de importar: preços devem ser números, datas devem seguir o formato português (DD/MM/AAAA).",
                "priority": "high" if count > 5 else "medium"
            })
        
        # Padrão: Erros de NIF
        elif "nif" in error_text or "5" in error_text and "empresa" in error_text:
            suggestions.append({
                "category": "data_quality",
                "title": "Problemas com NIFs",
                "description": f"Detectados {count} erros relacionados com NIFs. Lembre-se: NIFs que começam por 5 são de empresas.",
                "action": "Verificar NIFs antes de importar. Clientes particulares devem ter NIFs que começam por 1, 2, 3 ou 4.",
                "priority": "medium"
            })
        
        # Padrão: Erros de distrito/concelho
        elif any(word in error_text for word in ["distrito", "concelho", "localização", "localizacao"]):
            suggestions.append({
                "category": "geography",
                "title": "Erros de localização",
                "description": f"Detectados {count} erros de distrito/concelho. Verifique se os nomes estão correctos e completos.",
                "action": "Usar nomes oficiais dos distritos e concelhos portugueses. Evitar abreviaturas.",
                "priority": "medium"
            })
        
        # Padrão: Erros de proprietário
        elif any(word in error_text for word in ["proprietário", "proprietario", "owner"]):
            suggestions.append({
                "category": "owner_data",
                "title": "Dados do proprietário incompletos",
                "description": f"Detectados {count} erros relacionados com dados do proprietário.",
                "action": "Certifique-se de que o nome do proprietário está sempre preenchido. Telefone e email são opcionais mas recomendados.",
                "priority": "medium"
            })
        
        # Padrão genérico
        else:
            suggestions.append({
                "category": "other",
                "title": "Padrão de erro recorrente",
                "description": f"Detectados {count} erros com o padrão: '{pattern['_id'][:80]}...'",
                "action": "Analisar manualmente os ficheiros com este erro para identificar a causa.",
                "priority": "low"
            })
    
    # Adicionar sugestão baseada nas fontes de erro
    for source in sources:
        if source["_id"] == "excel_import" and source["count"] > 5:
            suggestions.insert(0, {
                "category": "process",
                "title": "Muitos erros na importação Excel",
                "description": f"A importação Excel gerou {source['count']} erros. Considere:",
                "action": "1. Verificar o formato do ficheiro antes de importar\n2. Usar o template oficial\n3. Pré-validar os dados numa folha de cálculo",
                "priority": "high"
            })
        elif source["_id"] == "document_analysis" and source["count"] > 10:
            suggestions.insert(0, {
                "category": "documents",
                "title": "Erros na análise de documentos",
                "description": f"A análise de documentos teve {source['count']} erros. Possíveis causas:",
                "action": "1. Verificar a qualidade das digitalizações\n2. Usar PDFs em vez de imagens\n3. Garantir que o nome do ficheiro corresponde ao cliente",
                "priority": "high"
            })
    
    # Remover duplicados mantendo ordem
    seen_titles = set()
    unique_suggestions = []
    for s in suggestions:
        if s["title"] not in seen_titles:
            seen_titles.add(s["title"])
            unique_suggestions.append(s)
    
    # Ordenar por prioridade
    priority_order = {"high": 0, "medium": 1, "low": 2}
    unique_suggestions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
    
    return {
        "total_errors": total_errors,
        "analyzed_patterns": len(patterns),
        "suggestions": unique_suggestions[:10],  # Limitar a 10 sugestões
        "patterns": [{"pattern": p["_id"][:100], "count": p["count"]} for p in patterns],
        "sources": [{"source": s["_id"], "count": s["count"]} for s in sources]
    }

@router.get("/weekly-report")
async def get_weekly_error_report(
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """
    Obtém o relatório semanal de análise de erros.
    
    A IA analisa os erros da última semana e gera:
    - Sumário dos erros por tipo e padrão
    - Sugestões de resolução prioritizadas
    - Itens de acção recomendados
    
    Este relatório é gerado automaticamente semanalmente e pode ser
    consultado a qualquer momento.
    """
    from services.error_analysis import get_latest_weekly_report
    
    report = await get_latest_weekly_report()
    return report


@router.post("/weekly-report/generate")
async def generate_weekly_error_report(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Força a geração de um novo relatório semanal.
    Útil para testar ou gerar análise actualizada.
    """
    from services.error_analysis import send_weekly_report_to_admin
    
    result = await send_weekly_report_to_admin()
    return result



# ==============================================================================
# ENDPOINTS PARA REVISÃO E COMPARAÇÃO DE DADOS EXTRAÍDOS
# ==============================================================================

@router.get("/extraction-history/{process_id}")
async def get_extraction_history(
    process_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO, UserRole.ADMINISTRATIVO]))
):
    """
    Obter histórico de extracções de IA para um processo.
    
    Mostra todos os dados extraídos de documentos, incluindo:
    - Dados que foram aplicados
    - Dados que foram ignorados (conflitos)
    - Pendentes de revisão (processos finalizados)
    
    Útil para:
    - Verificar o que a IA extraiu vs. o que está no sistema
    - Identificar dados que podem ter sido ignorados incorrectamente
    - Auditar alterações automáticas
    """
    process = await db.processes.find_one(
        {"id": process_id},
        {"_id": 0, "client_name": 1, "status": 1, 
         "ai_extraction_history": 1, "ai_pending_review": 1,
         "manually_edited_fields": 1, "personal_data": 1, 
         "financial_data": 1, "real_estate_data": 1}
    )
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    return {
        "process_id": process_id,
        "client_name": process.get("client_name"),
        "status": process.get("status"),
        "manually_edited_fields": process.get("manually_edited_fields", []),
        "extraction_history": process.get("ai_extraction_history", []),
        "pending_review": process.get("ai_pending_review", []),
        "current_data": {
            "personal": process.get("personal_data"),
            "financial": process.get("financial_data"),
            "real_estate": process.get("real_estate_data")
        }
    }


@router.get("/pending-reviews")
async def get_pending_reviews(
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO, UserRole.ADMINISTRATIVO]))
):
    """
    Listar todos os processos com dados pendentes de revisão.
    
    Inclui processos finalizados (concluído/desistido) onde a IA
    extraiu dados mas não os aplicou automaticamente.
    """
    # Buscar processos com ai_pending_review não vazio
    processes = await db.processes.find(
        {"ai_pending_review": {"$exists": True, "$ne": []}},
        {"_id": 0, "id": 1, "client_name": 1, "status": 1, "ai_pending_review": 1}
    ).to_list(100)
    
    result = []
    for proc in processes:
        pending = proc.get("ai_pending_review", [])
        result.append({
            "process_id": proc.get("id"),
            "client_name": proc.get("client_name"),
            "status": proc.get("status"),
            "pending_count": len(pending),
            "document_types": list(set(p.get("document_type") for p in pending)),
            "oldest_pending": min(p.get("extracted_at") for p in pending) if pending else None
        })
    
    return {
        "total_processes": len(result),
        "processes": result
    }


@router.post("/apply-pending/{process_id}")
async def apply_pending_review(
    process_id: str,
    item_index: int = 0,
    force: bool = False,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Aplicar dados pendentes de revisão a um processo.
    
    Parâmetros:
    - process_id: ID do processo
    - item_index: Índice do item pendente a aplicar (0 = primeiro)
    - force: Se True, sobrescreve dados existentes
    
    Após aplicação bem-sucedida, o item é removido da lista de pendentes.
    """
    process = await db.processes.find_one(
        {"id": process_id},
        {"_id": 0, "ai_pending_review": 1, "client_name": 1}
    )
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    pending = process.get("ai_pending_review", [])
    if item_index >= len(pending):
        raise HTTPException(status_code=400, detail="Índice inválido")
    
    item = pending[item_index]
    
    # Aplicar os dados
    updated, fields, conflicts = await update_client_data(
        process_id,
        item.get("extracted_data", {}),
        item.get("document_type", "outro"),
        force_update=force
    )
    
    if updated:
        # Remover o item da lista de pendentes
        await db.processes.update_one(
            {"id": process_id},
            {
                "$pull": {"ai_pending_review": {"extracted_at": item.get("extracted_at")}},
                "$push": {
                    "ai_extraction_history": {
                        "document_type": item.get("document_type"),
                        "extracted_at": item.get("extracted_at"),
                        "applied_at": datetime.now(timezone.utc).isoformat(),
                        "applied_by": user.get("email"),
                        "extracted_data": item.get("extracted_data"),
                        "applied_fields": fields,
                        "was_pending_review": True
                    }
                }
            }
        )
    
    return {
        "success": updated,
        "applied_fields": fields,
        "conflicts": conflicts,
        "message": f"Dados aplicados ao processo '{process.get('client_name')}'"
    }


@router.delete("/discard-pending/{process_id}")
async def discard_pending_review(
    process_id: str,
    item_index: int = 0,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Descartar dados pendentes de revisão (marcar como ignorados).
    
    Útil quando os dados extraídos estão incorrectos ou já não são necessários.
    """
    process = await db.processes.find_one(
        {"id": process_id},
        {"_id": 0, "ai_pending_review": 1}
    )
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    pending = process.get("ai_pending_review", [])
    if item_index >= len(pending):
        raise HTTPException(status_code=400, detail="Índice inválido")
    
    item = pending[item_index]
    
    # Remover da lista de pendentes
    await db.processes.update_one(
        {"id": process_id},
        {
            "$pull": {"ai_pending_review": {"extracted_at": item.get("extracted_at")}},
            "$push": {
                "ai_discarded_extractions": {
                    **item,
                    "discarded_at": datetime.now(timezone.utc).isoformat(),
                    "discarded_by": user.get("email")
                }
            }
        }
    )
    
    return {
        "success": True,
        "message": f"Extracção de {item.get('document_type')} descartada"
    }


@router.post("/mark-field-manual/{process_id}")
async def mark_field_as_manual(
    process_id: str,
    field_name: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO, UserRole.ADMINISTRATIVO, UserRole.CONSULTOR]))
):
    """
    Marcar um campo como editado manualmente.
    
    Campos marcados como manuais NÃO serão sobrescritos pela IA durante
    a importação de documentos.
    
    Exemplo: mark_field_manual("abc123", "personal_data.nif")
    """
    result = await db.processes.update_one(
        {"id": process_id},
        {
            "$addToSet": {"manually_edited_fields": field_name},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    if result.modified_count > 0:
        return {
            "success": True,
            "message": f"Campo '{field_name}' marcado como editado manualmente"
        }
    else:
        return {
            "success": False,
            "message": "Processo não encontrado ou campo já marcado"
        }


@router.delete("/unmark-field-manual/{process_id}")
async def unmark_field_as_manual(
    process_id: str,
    field_name: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Remover marcação de campo manual.
    
    Permite que a IA volte a actualizar o campo durante importações futuras.
    """
    result = await db.processes.update_one(
        {"id": process_id},
        {
            "$pull": {"manually_edited_fields": field_name},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    if result.modified_count > 0:
        return {
            "success": True,
            "message": f"Campo '{field_name}' pode ser actualizado pela IA novamente"
        }
    else:
        return {
            "success": False,
            "message": "Processo não encontrado ou campo não estava marcado"
        }


@router.get("/compare-data/{process_id}")
async def compare_extracted_vs_current(
    process_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO, UserRole.ADMINISTRATIVO]))
):
    """
    Comparar dados extraídos vs. dados actuais do processo.
    
    Mostra lado-a-lado:
    - Dados actuais no sistema
    - Último dado extraído pela IA para cada campo
    - Se há diferenças
    
    Útil para verificar se a IA está a extrair dados correctos e
    se há dados que devem ser revistos.
    """
    process = await db.processes.find_one(
        {"id": process_id},
        {"_id": 0}
    )
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Dados actuais
    current_data = {
        "personal_data": process.get("personal_data", {}),
        "financial_data": process.get("financial_data", {}),
        "real_estate_data": process.get("real_estate_data", {}),
        "client_name": process.get("client_name"),
        "client_email": process.get("client_email"),
        "client_phone": process.get("client_phone"),
        "client_nif": process.get("client_nif")
    }
    
    # Último dado extraído por campo (do histórico)
    extraction_history = process.get("ai_extraction_history", [])
    latest_extractions = {}
    
    for extraction in extraction_history:
        extracted = extraction.get("extracted_data", {})
        for key, value in extracted.items():
            if value:
                latest_extractions[key] = {
                    "value": value,
                    "document_type": extraction.get("document_type"),
                    "extracted_at": extraction.get("extracted_at")
                }
    
    # Dados pendentes de revisão
    pending = process.get("ai_pending_review", [])
    pending_data = {}
    for item in pending:
        extracted = item.get("extracted_data", {})
        for key, value in extracted.items():
            if value:
                pending_data[key] = {
                    "value": value,
                    "document_type": item.get("document_type"),
                    "extracted_at": item.get("extracted_at")
                }
    
    # Comparar e identificar diferenças
    comparisons = []
    all_keys = set(latest_extractions.keys()) | set(pending_data.keys())
    
    for key in all_keys:
        current_value = None
        
        # Tentar obter valor actual
        if "." in key:
            parts = key.split(".", 1)
            current_value = current_data.get(parts[0], {}).get(parts[1]) if isinstance(current_data.get(parts[0]), dict) else None
        else:
            current_value = current_data.get(key)
        
        latest = latest_extractions.get(key, {})
        pending = pending_data.get(key, {})
        
        comparison = {
            "field": key,
            "current_value": current_value,
            "latest_extracted": latest.get("value"),
            "latest_document": latest.get("document_type"),
            "latest_date": latest.get("extracted_at"),
            "pending_value": pending.get("value"),
            "pending_document": pending.get("document_type"),
            "has_difference": False
        }
        
        # Verificar se há diferença
        if latest.get("value") and current_value != latest.get("value"):
            comparison["has_difference"] = True
        if pending.get("value") and current_value != pending.get("value"):
            comparison["has_difference"] = True
            comparison["has_pending"] = True
        
        comparisons.append(comparison)
    
    # Ordenar por campos com diferenças primeiro
    comparisons.sort(key=lambda x: (not x.get("has_difference"), not x.get("has_pending", False), x["field"]))
    
    return {
        "process_id": process_id,
        "client_name": process.get("client_name"),
        "status": process.get("status"),
        "total_fields_compared": len(comparisons),
        "fields_with_differences": len([c for c in comparisons if c.get("has_difference")]),
        "fields_pending": len([c for c in comparisons if c.get("has_pending")]),
        "comparisons": comparisons
    }
