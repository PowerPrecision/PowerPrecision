"""
Rotas para gestão de Imóveis Angariados
CRUD completo para imóveis listados pela agência
"""
import uuid
import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, UploadFile, File

from database import db
from models.property import (
    Property, PropertyCreate, PropertyUpdate, PropertyListItem,
    PropertyStatus, PropertyType, PropertyHistory
)
from services.auth import get_current_user, require_roles
from services.alerts import check_and_notify_matches_for_new_property
from models.auth import UserRole

router = APIRouter(prefix="/properties", tags=["Properties"])
logger = logging.getLogger(__name__)


async def get_next_reference() -> str:
    """Gera próxima referência interna (IMO-001, IMO-002...)"""
    last = await db.properties.find_one(
        {"internal_reference": {"$regex": "^IMO-"}},
        sort=[("internal_reference", -1)]
    )
    if last and last.get("internal_reference"):
        try:
            num = int(last["internal_reference"].split("-")[1])
            return f"IMO-{num + 1:03d}"
        except (ValueError, IndexError):
            pass
    return "IMO-001"


@router.get("", response_model=List[PropertyListItem])
async def list_properties(
    status: Optional[PropertyStatus] = None,
    property_type: Optional[PropertyType] = None,
    district: Optional[str] = None,
    municipality: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_bedrooms: Optional[int] = None,
    agent_id: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Listar imóveis com filtros."""
    query = {}
    
    if status:
        query["status"] = status
    if property_type:
        query["property_type"] = property_type
    if district:
        query["address.district"] = {"$regex": district, "$options": "i"}
    if municipality:
        query["address.municipality"] = {"$regex": municipality, "$options": "i"}
    if min_price:
        query["financials.asking_price"] = {"$gte": min_price}
    if max_price:
        query.setdefault("financials.asking_price", {})["$lte"] = max_price
    if min_bedrooms:
        query["features.bedrooms"] = {"$gte": min_bedrooms}
    if agent_id:
        query["assigned_agent_id"] = agent_id
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"internal_reference": {"$regex": search, "$options": "i"}},
            {"address.locality": {"$regex": search, "$options": "i"}},
        ]
    
    properties = await db.properties.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Converter para formato de listagem
    result = []
    for p in properties:
        result.append(PropertyListItem(
            id=p["id"],
            internal_reference=p.get("internal_reference"),
            title=p["title"],
            property_type=p["property_type"],
            status=p["status"],
            asking_price=p["financials"]["asking_price"],
            municipality=p["address"]["municipality"],
            district=p["address"]["district"],
            bedrooms=p.get("features", {}).get("bedrooms") if p.get("features") else None,
            useful_area=p.get("features", {}).get("useful_area") if p.get("features") else None,
            photo_url=p["photos"][0] if p.get("photos") else None,
            assigned_agent_name=p.get("assigned_agent_name"),
            created_at=p["created_at"]
        ))
    
    return result


@router.get("/stats")
async def get_property_stats(user: dict = Depends(get_current_user)):
    """Obter estatísticas dos imóveis."""
    pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_value": {"$sum": "$financials.asking_price"}
            }
        }
    ]
    
    stats_cursor = db.properties.aggregate(pipeline)
    status_stats = {s["_id"]: {"count": s["count"], "total_value": s["total_value"]} 
                    async for s in stats_cursor}
    
    total = await db.properties.count_documents({})
    
    return {
        "total": total,
        "by_status": status_stats,
        "disponivel": status_stats.get("disponivel", {"count": 0, "total_value": 0}),
        "reservado": status_stats.get("reservado", {"count": 0, "total_value": 0}),
        "vendido": status_stats.get("vendido", {"count": 0, "total_value": 0}),
    }


@router.post("", response_model=Property)
async def create_property(
    data: PropertyCreate,
    user: dict = Depends(get_current_user)
):
    """Criar novo imóvel angariado."""
    now = datetime.now(timezone.utc).isoformat()
    
    # Gerar referência se não fornecida
    internal_ref = data.internal_reference or await get_next_reference()
    
    # Obter nome do agente se atribuído
    agent_name = None
    if data.assigned_agent_id:
        agent = await db.users.find_one({"id": data.assigned_agent_id}, {"name": 1})
        if agent:
            agent_name = agent["name"]
    
    property_doc = Property(
        id=str(uuid.uuid4()),
        internal_reference=internal_ref,
        property_type=data.property_type,
        title=data.title,
        description=data.description,
        address=data.address,
        features=data.features,
        condition=data.condition,
        financials=data.financials,
        owner=data.owner,
        photos=data.photos,
        video_url=data.video_url,
        virtual_tour_url=data.virtual_tour_url,
        documents=data.documents,
        status=data.status,
        assigned_agent_id=data.assigned_agent_id,
        assigned_agent_name=agent_name,
        notes=data.notes,
        private_notes=data.private_notes,
        history=[
            PropertyHistory(
                timestamp=now,
                event="Imóvel criado",
                user=user.get("email")
            )
        ],
        created_at=now,
        updated_at=now,
        created_by=user.get("email")
    )
    
    await db.properties.insert_one(property_doc.model_dump())
    
    logger.info(f"Imóvel criado: {property_doc.id} ({internal_ref}) por {user.get('email')}")
    
    # Verificar matches em background (não bloqueia resposta)
    asyncio.create_task(check_and_notify_matches_for_new_property(property_doc.id))
    
    return property_doc


@router.get("/{property_id}", response_model=Property)
async def get_property(
    property_id: str,
    user: dict = Depends(get_current_user)
):
    """Obter detalhes de um imóvel."""
    prop = await db.properties.find_one({"id": property_id}, {"_id": 0})
    
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    
    # Incrementar contador de visualizações
    await db.properties.update_one(
        {"id": property_id},
        {"$inc": {"view_count": 1}}
    )
    
    return Property(**prop)


@router.patch("/{property_id}", response_model=Property)
async def update_property(
    property_id: str,
    data: PropertyUpdate,
    user: dict = Depends(get_current_user)
):
    """Actualizar um imóvel."""
    prop = await db.properties.find_one({"id": property_id})
    
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Preparar actualização
    update_dict = data.model_dump(exclude_none=True)
    update_dict["updated_at"] = now
    
    # Actualizar nome do agente se mudou
    if "assigned_agent_id" in update_dict:
        agent = await db.users.find_one({"id": update_dict["assigned_agent_id"]}, {"name": 1})
        update_dict["assigned_agent_name"] = agent["name"] if agent else None
    
    # Registar mudança de status no histórico
    if "status" in update_dict and update_dict["status"] != prop.get("status"):
        history_entry = PropertyHistory(
            timestamp=now,
            event=f"Status alterado para {update_dict['status']}",
            user=user.get("email")
        )
        await db.properties.update_one(
            {"id": property_id},
            {"$push": {"history": history_entry.model_dump()}}
        )
    
    await db.properties.update_one(
        {"id": property_id},
        {"$set": update_dict}
    )
    
    updated = await db.properties.find_one({"id": property_id}, {"_id": 0})
    
    return Property(**updated)


@router.patch("/{property_id}/status")
async def update_property_status(
    property_id: str,
    status: PropertyStatus,
    user: dict = Depends(get_current_user)
):
    """Actualizar apenas o status de um imóvel."""
    prop = await db.properties.find_one({"id": property_id})
    
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    history_entry = PropertyHistory(
        timestamp=now,
        event=f"Status alterado para {status.value}",
        user=user.get("email")
    )
    
    await db.properties.update_one(
        {"id": property_id},
        {
            "$set": {"status": status.value, "updated_at": now},
            "$push": {"history": history_entry.model_dump()}
        }
    )
    
    return {"success": True, "status": status.value}


@router.delete("/{property_id}")
async def delete_property(
    property_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO, UserRole.DIRETOR]))
):
    """Eliminar um imóvel (apenas admin/CEO/diretor)."""
    result = await db.properties.delete_one({"id": property_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    
    logger.info(f"Imóvel {property_id} eliminado por {user.get('email')}")
    
    return {"success": True, "message": "Imóvel eliminado"}


@router.post("/{property_id}/interested-client")
async def add_interested_client(
    property_id: str,
    client_id: str,
    user: dict = Depends(get_current_user)
):
    """Adicionar cliente interessado a um imóvel."""
    prop = await db.properties.find_one({"id": property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    
    # Verificar se cliente existe
    process = await db.processes.find_one({"id": client_id})
    if not process:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Adicionar se não existe
    if client_id not in prop.get("interested_clients", []):
        now = datetime.now(timezone.utc).isoformat()
        await db.properties.update_one(
            {"id": property_id},
            {
                "$addToSet": {"interested_clients": client_id},
                "$inc": {"inquiry_count": 1},
                "$push": {
                    "history": PropertyHistory(
                        timestamp=now,
                        event=f"Cliente interessado: {process.get('client_name')}",
                        user=user.get("email")
                    ).model_dump()
                }
            }
        )
    
    return {"success": True, "message": f"Cliente {process.get('client_name')} adicionado"}


@router.get("/{property_id}/interested-clients")
async def get_interested_clients(
    property_id: str,
    user: dict = Depends(get_current_user)
):
    """Obter lista de clientes interessados num imóvel."""
    prop = await db.properties.find_one({"id": property_id}, {"interested_clients": 1})
    
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    
    client_ids = prop.get("interested_clients", [])
    
    if not client_ids:
        return []
    
    clients = await db.processes.find(
        {"id": {"$in": client_ids}},
        {"_id": 0, "id": 1, "client_name": 1, "client_email": 1, "client_phone": 1, "status": 1}
    ).to_list(100)
    
    return clients


@router.post("/{property_id}/register-visit")
async def register_visit(
    property_id: str,
    client_id: Optional[str] = None,
    notes: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Registar uma visita ao imóvel."""
    prop = await db.properties.find_one({"id": property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    event_text = "Visita registada"
    if client_id:
        process = await db.processes.find_one({"id": client_id}, {"client_name": 1})
        if process:
            event_text = f"Visita com {process.get('client_name')}"
    
    if notes:
        event_text += f" - {notes}"
    
    await db.properties.update_one(
        {"id": property_id},
        {
            "$inc": {"visit_count": 1},
            "$push": {
                "history": PropertyHistory(
                    timestamp=now,
                    event=event_text,
                    user=user.get("email")
                ).model_dump()
            }
        }
    )
    
    return {"success": True, "message": "Visita registada"}



@router.post("/{property_id}/upload-photo")
async def upload_property_photo(
    property_id: str,
    photo_url: str,
    user: dict = Depends(get_current_user)
):
    """
    Adicionar foto a um imóvel.
    Aceita URL de foto (pode ser do OneDrive, Dropbox, etc.)
    """
    prop = await db.properties.find_one({"id": property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.properties.update_one(
        {"id": property_id},
        {
            "$addToSet": {"photos": photo_url},
            "$set": {"updated_at": now},
            "$push": {
                "history": PropertyHistory(
                    timestamp=now,
                    event="Foto adicionada",
                    user=user.get("email")
                ).model_dump()
            }
        }
    )
    
    return {"success": True, "message": "Foto adicionada", "photo_url": photo_url}


@router.delete("/{property_id}/photo")
async def remove_property_photo(
    property_id: str,
    photo_url: str,
    user: dict = Depends(get_current_user)
):
    """Remover foto de um imóvel."""
    prop = await db.properties.find_one({"id": property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.properties.update_one(
        {"id": property_id},
        {
            "$pull": {"photos": photo_url},
            "$set": {"updated_at": now}
        }
    )
    
    return {"success": True, "message": "Foto removida"}


@router.post("/bulk/import-excel")
async def import_properties_from_excel(
    file: UploadFile,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO, UserRole.DIRETOR]))
):
    """
    Importar imóveis a partir de ficheiro Excel.
    
    Colunas esperadas (case-insensitive):
    - titulo (obrigatório): Título do imóvel
    - tipo: apartamento, moradia, terreno, loja, escritorio, armazem, garagem, outro
    - preco (obrigatório): Preço pedido
    - distrito (obrigatório): Ex: Lisboa, Porto
    - concelho (obrigatório): Ex: Lisboa, Cascais
    - localidade: Ex: Cascais, Oeiras
    - morada: Endereço completo
    - codigo_postal: Ex: 2750-123
    - quartos: Número de quartos (T0=0, T1=1, etc.)
    - casas_banho: Número de casas de banho
    - area_util: Área útil em m²
    - area_bruta: Área bruta em m²
    - ano_construcao: Ano de construção
    - certificado_energetico: A, B, C, D, E, F, G
    - estado: novo, como_novo, bom, para_recuperar, em_construcao
    - proprietario_nome (obrigatório): Nome do proprietário
    - proprietario_telefone: Telefone do proprietário
    - proprietario_email: Email do proprietário
    - descricao: Descrição do imóvel
    - notas: Notas internas
    """
    import pandas as pd
    from io import BytesIO
    
    # Validar tipo de ficheiro
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Ficheiro deve ser Excel (.xlsx ou .xls)")
    
    # Ler ficheiro
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        logger.error(f"Erro ao ler ficheiro Excel: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao ler ficheiro: {str(e)}")
    
    # Normalizar nomes das colunas (lowercase, sem espaços)
    df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
    
    # Mapear tipos de imóvel
    tipo_map = {
        'apartamento': 'apartamento',
        'moradia': 'moradia',
        'terreno': 'terreno',
        'loja': 'loja',
        'escritorio': 'escritorio',
        'escritório': 'escritorio',
        'armazem': 'armazem',
        'armazém': 'armazem',
        'garagem': 'garagem',
        'outro': 'outro'
    }
    
    # Mapear estados
    estado_map = {
        'novo': 'novo',
        'como_novo': 'como_novo',
        'como novo': 'como_novo',
        'bom': 'bom',
        'para_recuperar': 'para_recuperar',
        'para recuperar': 'para_recuperar',
        'em_construcao': 'em_construcao',
        'em construção': 'em_construcao',
        'em construcao': 'em_construcao'
    }
    
    results = {
        "total": len(df),
        "importados": 0,
        "erros": [],
        "ids_criados": []
    }
    
    now = datetime.now(timezone.utc).isoformat()
    
    for idx, row in df.iterrows():
        linha = idx + 2  # +2 porque idx começa em 0 e Excel tem cabeçalho
        
        try:
            # Campos obrigatórios
            titulo = str(row.get('titulo', '')).strip()
            if not titulo or titulo == 'nan':
                results["erros"].append({"linha": linha, "erro": "Título em falta"})
                continue
            
            preco = row.get('preco') or row.get('preço')
            if pd.isna(preco):
                results["erros"].append({"linha": linha, "erro": "Preço em falta"})
                continue
            preco = float(preco)
            
            distrito = str(row.get('distrito', '')).strip()
            if not distrito or distrito == 'nan':
                results["erros"].append({"linha": linha, "erro": "Distrito em falta"})
                continue
            
            concelho = str(row.get('concelho', '')).strip()
            if not concelho or concelho == 'nan':
                results["erros"].append({"linha": linha, "erro": "Concelho em falta"})
                continue
            
            proprietario_nome = str(row.get('proprietario_nome', '') or row.get('proprietário_nome', '')).strip()
            if not proprietario_nome or proprietario_nome == 'nan':
                results["erros"].append({"linha": linha, "erro": "Nome do proprietário em falta"})
                continue
            
            # Campos opcionais
            tipo = str(row.get('tipo', 'apartamento')).lower().strip()
            tipo = tipo_map.get(tipo, 'apartamento')
            
            estado = str(row.get('estado', 'bom')).lower().strip()
            estado = estado_map.get(estado, 'bom')
            
            # Criar documento
            internal_ref = await get_next_reference()
            
            property_doc = {
                "id": str(uuid.uuid4()),
                "internal_reference": internal_ref,
                "property_type": tipo,
                "title": titulo,
                "description": str(row.get('descricao', '') or '').strip() if not pd.isna(row.get('descricao')) else None,
                "address": {
                    "street": str(row.get('morada', '') or '').strip() if not pd.isna(row.get('morada')) else None,
                    "postal_code": str(row.get('codigo_postal', '') or '').strip() if not pd.isna(row.get('codigo_postal')) else None,
                    "locality": str(row.get('localidade', '') or '').strip() if not pd.isna(row.get('localidade')) else None,
                    "municipality": concelho,
                    "district": distrito
                },
                "features": {
                    "bedrooms": int(row.get('quartos')) if not pd.isna(row.get('quartos')) else None,
                    "bathrooms": int(row.get('casas_banho')) if not pd.isna(row.get('casas_banho')) else None,
                    "useful_area": float(row.get('area_util')) if not pd.isna(row.get('area_util')) else None,
                    "gross_area": float(row.get('area_bruta')) if not pd.isna(row.get('area_bruta')) else None,
                    "construction_year": int(row.get('ano_construcao')) if not pd.isna(row.get('ano_construcao')) else None,
                    "energy_certificate": str(row.get('certificado_energetico', '')).upper().strip() if not pd.isna(row.get('certificado_energetico')) else None,
                    "extra_features": []
                },
                "condition": estado,
                "financials": {
                    "asking_price": preco
                },
                "owner": {
                    "name": proprietario_nome,
                    "phone": str(row.get('proprietario_telefone', '') or row.get('proprietário_telefone', '')).strip() if not pd.isna(row.get('proprietario_telefone', row.get('proprietário_telefone'))) else None,
                    "email": str(row.get('proprietario_email', '') or row.get('proprietário_email', '')).strip() if not pd.isna(row.get('proprietario_email', row.get('proprietário_email'))) else None
                },
                "photos": [],
                "documents": [],
                "status": "em_analise",
                "notes": str(row.get('notas', '') or '').strip() if not pd.isna(row.get('notas')) else None,
                "history": [{
                    "timestamp": now,
                    "event": "Importado via Excel",
                    "user": user.get("email")
                }],
                "created_at": now,
                "updated_at": now,
                "created_by": user.get("email"),
                "view_count": 0,
                "inquiry_count": 0,
                "visit_count": 0,
                "interested_clients": []
            }
            
            await db.properties.insert_one(property_doc)
            results["importados"] += 1
            results["ids_criados"].append(property_doc["id"])
            
            logger.info(f"Imóvel importado: {internal_ref} - {titulo}")
            
        except Exception as e:
            logger.error(f"Erro na linha {linha}: {e}")
            results["erros"].append({"linha": linha, "erro": str(e)})
    
    # Log de erros para análise
    if results["erros"]:
        for err in results["erros"]:
            await db.error_logs.insert_one({
                "timestamp": now,
                "source": "excel_import",
                "error_message": err["erro"],
                "raw_data": f"Linha {err['linha']}",
                "user": user.get("email")
            })
    
    return results


@router.get("/bulk/import-template")
async def get_import_template(user: dict = Depends(get_current_user)):
    """
    Retorna instruções para o template de importação Excel.
    """
    return {
        "instrucoes": "Crie um ficheiro Excel (.xlsx) com as seguintes colunas:",
        "colunas_obrigatorias": [
            {"nome": "titulo", "descricao": "Título do imóvel", "exemplo": "T2 em Cascais"},
            {"nome": "preco", "descricao": "Preço pedido", "exemplo": "250000"},
            {"nome": "distrito", "descricao": "Distrito", "exemplo": "Lisboa"},
            {"nome": "concelho", "descricao": "Concelho", "exemplo": "Cascais"},
            {"nome": "proprietario_nome", "descricao": "Nome do proprietário", "exemplo": "João Silva"}
        ],
        "colunas_opcionais": [
            {"nome": "tipo", "valores": "apartamento, moradia, terreno, loja, escritorio, armazem, garagem, outro"},
            {"nome": "localidade", "exemplo": "Cascais"},
            {"nome": "morada", "exemplo": "Rua das Flores, 123"},
            {"nome": "codigo_postal", "exemplo": "2750-123"},
            {"nome": "quartos", "exemplo": "2"},
            {"nome": "casas_banho", "exemplo": "1"},
            {"nome": "area_util", "exemplo": "85"},
            {"nome": "area_bruta", "exemplo": "100"},
            {"nome": "ano_construcao", "exemplo": "2010"},
            {"nome": "certificado_energetico", "valores": "A, B, C, D, E, F, G"},
            {"nome": "estado", "valores": "novo, como_novo, bom, para_recuperar, em_construcao"},
            {"nome": "proprietario_telefone", "exemplo": "+351 912345678"},
            {"nome": "proprietario_email", "exemplo": "email@exemplo.com"},
            {"nome": "descricao", "exemplo": "Apartamento renovado com vista mar"},
            {"nome": "notas", "exemplo": "Notas internas"}
        ]
    }

