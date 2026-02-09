"""
Rotas para gestão de Clientes

Permite gerir clientes de forma independente dos processos.
Um cliente pode ter múltiplos processos de compra/financiamento.
"""

import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query

from database import db
from models.client import (
    Client, ClientCreate, ClientUpdate, 
    ClientContact, ClientPersonalData, ClientFinancialData,
    find_or_create_client_key
)
from services.auth import get_current_user, require_roles
from models.auth import UserRole

router = APIRouter(prefix="/clients", tags=["Clients"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_clients(
    search: Optional[str] = Query(None, description="Pesquisar por nome, email ou NIF"),
    has_active_process: Optional[bool] = Query(None, description="Filtrar por ter processo activo"),
    limit: int = Query(100, le=500),
    skip: int = Query(0),
    user: dict = Depends(get_current_user)
):
    """
    Listar clientes.
    - Admin/CEO: vê todos os clientes
    - Consultor/Intermediário: vê clientes dos seus processos (ou todos se não houver atribuição)
    """
    user_role = user.get("role", "")
    user_id = user.get("id", "")
    user_email = user.get("email", "")
    
    # Para roles não-admin, buscar clientes a partir dos processos
    if user_role not in ["admin", "ceo", "diretor"]:
        # Primeiro verificar se há processos atribuídos a este utilizador
        my_processes_count = await db.processes.count_documents({
            "$or": [
                {"assigned_to": user_id},
                {"assigned_to": user_email},
                {"created_by": user_email}
            ]
        })
        
        # Se não houver processos atribuídos, mostrar todos os processos (legado)
        if my_processes_count == 0:
            process_query = {}
        else:
            process_query = {
                "$or": [
                    {"assigned_to": user_id},
                    {"assigned_to": user_email},
                    {"created_by": user_email}
                ]
            }
        
        if search:
            search_filter = {
                "$or": [
                    {"client_name": {"$regex": search, "$options": "i"}},
                    {"client_email": {"$regex": search, "$options": "i"}},
                    {"personal_data.nif": {"$regex": search, "$options": "i"}}
                ]
            }
            if process_query:
                process_query = {"$and": [process_query, search_filter]}
            else:
                process_query = search_filter
        
        # Buscar processos e transformar em "clientes"
        processes = await db.processes.find(
            process_query,
            {"_id": 0, "id": 1, "client_name": 1, "client_email": 1, "client_phone": 1, 
             "personal_data": 1, "status": 1, "process_number": 1, "client_id": 1}
        ).skip(skip).limit(limit).to_list(length=limit)
        
        # Agrupar por cliente (usando client_id ou client_name como chave)
        clients_map = {}
        for proc in processes:
            key = proc.get("client_id") or proc.get("client_name", "").lower().strip()
            if not key:
                continue
            
            if key not in clients_map:
                clients_map[key] = {
                    "id": proc.get("client_id") or f"process_{proc.get('id')}",
                    "nome": proc.get("client_name"),
                    "contacto": {
                        "email": proc.get("client_email"),
                        "telefone": proc.get("client_phone")
                    },
                    "dados_pessoais": proc.get("personal_data") or {},
                    "process_ids": [],
                    "active_processes_count": 0,
                    "source": "processes"
                }
            
            clients_map[key]["process_ids"].append(proc.get("id"))
            if proc.get("status") not in ["arquivado", "cancelado", "concluido"]:
                clients_map[key]["active_processes_count"] += 1
        
        clients = list(clients_map.values())
        
        if has_active_process is not None:
            if has_active_process:
                clients = [c for c in clients if c.get("active_processes_count", 0) > 0]
            else:
                clients = [c for c in clients if c.get("active_processes_count", 0) == 0]
        
        return {
            "clients": clients,
            "total": len(clients),
            "limit": limit,
            "skip": skip
        }
    
    # Para admin/CEO - buscar da colecção clients + processes sem client_id
    query = {}
    
    if search:
        query["$or"] = [
            {"nome": {"$regex": search, "$options": "i"}},
            {"contacto.email": {"$regex": search, "$options": "i"}},
            {"dados_pessoais.nif": {"$regex": search, "$options": "i"}}
        ]
    
    clients = await db.clients.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(length=limit)
    
    # Também incluir clientes de processos que não estão na colecção clients
    process_query = {"client_id": {"$exists": False}}
    if search:
        process_query["$or"] = [
            {"client_name": {"$regex": search, "$options": "i"}},
            {"client_email": {"$regex": search, "$options": "i"}}
        ]
    
    orphan_processes = await db.processes.find(
        process_query,
        {"_id": 0, "id": 1, "client_name": 1, "client_email": 1, "client_phone": 1, 
         "personal_data": 1, "status": 1}
    ).to_list(length=500)
    
    # Adicionar clientes "órfãos" (de processos sem client_id)
    existing_names = {c.get("nome", "").lower() for c in clients}
    orphan_map = {}
    for proc in orphan_processes:
        name = proc.get("client_name", "").strip()
        name_lower = name.lower()
        if not name or name_lower in existing_names:
            continue
        
        if name_lower not in orphan_map:
            orphan_map[name_lower] = {
                "id": f"process_{proc.get('id')}",
                "nome": name,
                "contacto": {
                    "email": proc.get("client_email"),
                    "telefone": proc.get("client_phone")
                },
                "dados_pessoais": proc.get("personal_data") or {},
                "process_ids": [proc.get("id")],
                "active_processes_count": 1 if proc.get("status") not in ["arquivado", "cancelado", "concluido"] else 0,
                "source": "processes"
            }
        else:
            orphan_map[name_lower]["process_ids"].append(proc.get("id"))
            if proc.get("status") not in ["arquivado", "cancelado", "concluido"]:
                orphan_map[name_lower]["active_processes_count"] += 1
    
    clients.extend(orphan_map.values())
    
    # Contar processos activos para clientes da colecção clients
    for client in clients:
        if client.get("source") != "processes" and client.get("process_ids"):
            active_count = await db.processes.count_documents({
                "id": {"$in": client["process_ids"]},
                "status": {"$nin": ["arquivado", "cancelado", "concluido"]}
            })
            client["active_processes_count"] = active_count
        elif "active_processes_count" not in client:
            client["active_processes_count"] = 0
    
    if has_active_process is not None:
        if has_active_process:
            clients = [c for c in clients if c.get("active_processes_count", 0) > 0]
        else:
            clients = [c for c in clients if c.get("active_processes_count", 0) == 0]
    
    total = len(clients)
    
    return {
        "clients": clients,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/{client_id}")
async def get_client(
    client_id: str,
    user: dict = Depends(get_current_user)
):
    """Obter detalhes de um cliente."""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Carregar detalhes dos processos
    processes = []
    if client.get("process_ids"):
        processes = await db.processes.find(
            {"id": {"$in": client["process_ids"]}},
            {"_id": 0, "id": 1, "process_number": 1, "status": 1, "process_type": 1, "created_at": 1}
        ).to_list(length=50)
    
    client["processes"] = processes
    
    return client


@router.post("", response_model=Client)
async def create_client(
    client_data: ClientCreate,
    user: dict = Depends(get_current_user)
):
    """Criar um novo cliente."""
    # Verificar se já existe cliente com mesmo NIF ou email
    existing_query = []
    if client_data.nif:
        existing_query.append({"dados_pessoais.nif": client_data.nif})
    if client_data.email:
        existing_query.append({"contacto.email": client_data.email.lower()})
    
    if existing_query:
        existing = await db.clients.find_one({"$or": existing_query})
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Já existe um cliente com este NIF ou email: {existing.get('nome')}"
            )
    
    now = datetime.now(timezone.utc).isoformat()
    
    client = Client(
        id=str(uuid.uuid4()),
        nome=client_data.nome,
        contacto=ClientContact(
            email=client_data.email.lower() if client_data.email else None,
            telefone=client_data.telefone
        ),
        dados_pessoais=ClientPersonalData(
            nif=client_data.nif
        ),
        fonte=client_data.fonte,
        notas=client_data.notas,
        created_at=now,
        updated_at=now,
        created_by=user.get("email")
    )
    
    await db.clients.insert_one(client.model_dump())
    
    logger.info(f"Cliente criado: {client.id} - {client.nome} por {user.get('email')}")
    
    return client


@router.put("/{client_id}")
async def update_client(
    client_id: str,
    client_data: ClientUpdate,
    user: dict = Depends(get_current_user)
):
    """Actualizar dados de um cliente."""
    client = await db.clients.find_one({"id": client_id})
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    update_dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if client_data.nome:
        update_dict["nome"] = client_data.nome
    if client_data.contacto:
        update_dict["contacto"] = client_data.contacto.model_dump(exclude_unset=True)
    if client_data.dados_pessoais:
        update_dict["dados_pessoais"] = client_data.dados_pessoais.model_dump(exclude_unset=True)
    if client_data.dados_financeiros:
        update_dict["dados_financeiros"] = client_data.dados_financeiros.model_dump(exclude_unset=True)
    if client_data.tags is not None:
        update_dict["tags"] = client_data.tags
    if client_data.notas is not None:
        update_dict["notas"] = client_data.notas
    
    await db.clients.update_one(
        {"id": client_id},
        {"$set": update_dict}
    )
    
    logger.info(f"Cliente {client_id} actualizado por {user.get('email')}")
    
    return {"success": True, "message": "Cliente actualizado"}


@router.post("/{client_id}/link-process")
async def link_process_to_client(
    client_id: str,
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Vincular um processo existente a um cliente.
    
    Isto permite que um cliente tenha múltiplos processos de compra.
    """
    # Verificar se cliente existe
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Verificar se processo existe
    process = await db.processes.find_one({"id": process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Verificar se já está vinculado
    if process_id in client.get("process_ids", []):
        return {"success": True, "message": "Processo já vinculado a este cliente"}
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Adicionar processo ao cliente
    await db.clients.update_one(
        {"id": client_id},
        {
            "$addToSet": {"process_ids": process_id},
            "$set": {"updated_at": now}
        }
    )
    
    # Actualizar processo com referência ao cliente
    await db.processes.update_one(
        {"id": process_id},
        {
            "$set": {
                "client_id": client_id,
                "updated_at": now
            }
        }
    )
    
    logger.info(f"Processo {process_id} vinculado ao cliente {client_id} por {user.get('email')}")
    
    return {
        "success": True,
        "message": f"Processo vinculado ao cliente {client.get('nome')}"
    }


@router.delete("/{client_id}/unlink-process/{process_id}")
async def unlink_process_from_client(
    client_id: str,
    process_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Desvincular um processo de um cliente (apenas admin/CEO)."""
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Remover processo do cliente
    await db.clients.update_one(
        {"id": client_id},
        {
            "$pull": {"process_ids": process_id},
            "$set": {"updated_at": now}
        }
    )
    
    # Remover referência ao cliente do processo
    await db.processes.update_one(
        {"id": process_id},
        {
            "$unset": {"client_id": ""},
            "$set": {"updated_at": now}
        }
    )
    
    logger.info(f"Processo {process_id} desvinculado do cliente {client_id} por {user.get('email')}")
    
    return {"success": True, "message": "Processo desvinculado"}


@router.post("/{client_id}/create-process")
async def create_process_for_client(
    client_id: str,
    process_type: str = Query("credito_habitacao", description="Tipo de processo"),
    description: Optional[str] = Query(None, description="Descrição do processo"),
    user: dict = Depends(get_current_user)
):
    """
    Criar um novo processo para um cliente existente.
    
    Isto permite que o mesmo cliente tenha múltiplos processos de compra.
    """
    # Verificar se cliente existe
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Obter próximo número de processo
    last_process = await db.processes.find_one(
        {},
        sort=[("process_number", -1)],
        projection={"process_number": 1}
    )
    next_number = (last_process.get("process_number", 0) if last_process else 0) + 1
    
    now = datetime.now(timezone.utc).isoformat()
    process_id = str(uuid.uuid4())
    
    # Criar novo processo com dados do cliente
    new_process = {
        "id": process_id,
        "process_number": next_number,
        "client_id": client_id,
        "client_name": client.get("nome"),
        "client_email": client.get("contacto", {}).get("email", ""),
        "client_phone": client.get("contacto", {}).get("telefone", ""),
        "process_type": process_type,
        "status": "novo",
        "description": description,
        # Copiar dados pessoais e financeiros do cliente
        "personal_data": client.get("dados_pessoais", {}),
        "financial_data": client.get("dados_financeiros", {}),
        "real_estate_data": {},
        "credit_data": {},
        # Co-compradores herdados do cliente
        "co_buyers": client.get("co_buyers", []),
        "co_applicants": client.get("co_applicants", []),
        # Metadados
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
        "source": "client_portal"
    }
    
    await db.processes.insert_one(new_process)
    
    # Adicionar processo ao cliente
    await db.clients.update_one(
        {"id": client_id},
        {
            "$addToSet": {"process_ids": process_id},
            "$set": {"updated_at": now}
        }
    )
    
    logger.info(f"Novo processo {process_id} criado para cliente {client_id} por {user.get('email')}")
    
    return {
        "success": True,
        "process_id": process_id,
        "process_number": next_number,
        "message": f"Processo #{next_number} criado para {client.get('nome')}"
    }


@router.get("/{client_id}/processes")
async def get_client_processes(
    client_id: str,
    include_archived: bool = Query(False),
    user: dict = Depends(get_current_user)
):
    """Obter todos os processos de um cliente."""
    client = await db.clients.find_one({"id": client_id})
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    process_ids = client.get("process_ids", [])
    
    if not process_ids:
        return {
            "client_name": client.get("nome"),
            "processes": [],
            "total": 0
        }
    
    query = {"id": {"$in": process_ids}}
    if not include_archived:
        query["status"] = {"$nin": ["arquivado", "cancelado"]}
    
    processes = await db.processes.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(length=50)
    
    return {
        "client_name": client.get("nome"),
        "processes": processes,
        "total": len(processes)
    }


@router.post("/find-or-create")
async def find_or_create_client(
    nome: str,
    email: Optional[str] = None,
    nif: Optional[str] = None,
    telefone: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Encontrar cliente existente ou criar novo.
    
    Procura por NIF, email ou nome similar.
    Se não encontrar, cria um novo cliente.
    """
    # Tentar encontrar por NIF
    if nif:
        existing = await db.clients.find_one({"dados_pessoais.nif": nif})
        if existing:
            return {
                "found": True,
                "client": existing,
                "match_type": "nif"
            }
    
    # Tentar encontrar por email
    if email:
        existing = await db.clients.find_one({"contacto.email": email.lower()})
        if existing:
            return {
                "found": True,
                "client": existing,
                "match_type": "email"
            }
    
    # Tentar encontrar por nome similar
    if nome:
        # Pesquisa fuzzy pelo nome
        from routes.ai_bulk import normalize_text_for_matching
        nome_norm = normalize_text_for_matching(nome)
        
        # Buscar candidatos
        candidates = await db.clients.find(
            {},
            {"_id": 0, "id": 1, "nome": 1}
        ).to_list(length=1000)
        
        for candidate in candidates:
            candidate_norm = normalize_text_for_matching(candidate.get("nome", ""))
            # Match exacto após normalização
            if nome_norm == candidate_norm:
                full_client = await db.clients.find_one({"id": candidate["id"]}, {"_id": 0})
                return {
                    "found": True,
                    "client": full_client,
                    "match_type": "nome"
                }
    
    # Não encontrou - criar novo cliente
    client_data = ClientCreate(
        nome=nome,
        email=email,
        telefone=telefone,
        nif=nif,
        fonte="auto_created"
    )
    
    new_client = await create_client(client_data, user)
    
    return {
        "found": False,
        "client": new_client.model_dump(),
        "match_type": "created"
    }


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO]))
):
    """Eliminar um cliente (apenas admin/CEO)."""
    client = await db.clients.find_one({"id": client_id})
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Verificar se tem processos activos
    if client.get("process_ids"):
        active_count = await db.processes.count_documents({
            "id": {"$in": client["process_ids"]},
            "status": {"$nin": ["arquivado", "cancelado", "concluido"]}
        })
        if active_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cliente tem {active_count} processo(s) activo(s). Archive-os primeiro."
            )
    
    await db.clients.delete_one({"id": client_id})
    
    logger.info(f"Cliente {client_id} eliminado por {user.get('email')}")
    
    return {"success": True, "message": "Cliente eliminado"}
