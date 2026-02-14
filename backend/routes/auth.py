import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Response

from database import db
from models.auth import (
    UserRole, UserRegister, UserLogin, UserResponse, TokenResponse
)
from services.auth import (
    hash_password, verify_password, create_token, get_current_user
)
from middleware.rate_limit import limiter


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
@limiter.limit("3/hour")
async def register(request: Request, response: Response, data: UserRegister):
    existing = await db.users.find_one({"email": data.email})
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Email já registado")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password": hash_password(data.password),
        "name": data.name,
        "phone": data.phone,
        "role": UserRole.CLIENTE,
        "is_active": True,
        "onedrive_folder": data.name,
        "created_at": now
    }
    
    await db.users.insert_one(user_doc)
    token = create_token(user_id, data.email, UserRole.CLIENTE)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=data.email,
            name=data.name,
            phone=data.phone,
            role=UserRole.CLIENTE,
            created_at=now,
            onedrive_folder=data.name
        )
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, data: UserLogin, response: Response):
    from fastapi import HTTPException
    
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    # Check password - support both "password" and "hashed_password" field names
    password_field = user.get("password") or user.get("hashed_password", "")
    if not verify_password(data.password, password_field):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Conta desativada")
    
    token = create_token(user["id"], user["email"], user["role"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            phone=user.get("phone"),
            role=user["role"],
            created_at=user["created_at"],
            onedrive_folder=user.get("onedrive_folder")
        )
    )


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Retorna o utilizador atual incluindo info de impersonate se aplicável."""
    response = {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "phone": user.get("phone"),
        "role": user["role"],
        "created_at": user["created_at"],
        "onedrive_folder": user.get("onedrive_folder"),
        "is_active": user.get("is_active", True)
    }
    
    # Incluir informação de impersonate se presente
    if user.get("is_impersonated"):
        response["is_impersonated"] = True
        response["impersonated_by"] = user.get("impersonated_by")
        response["impersonated_by_name"] = user.get("impersonated_by_name")
    
    return response



@router.put("/preferences")
async def update_preferences(
    data: dict,
    user: dict = Depends(get_current_user)
):
    """
    Atualiza as preferências de notificação do utilizador.
    """
    user_id = user["id"]
    
    # Extrair preferências de notificação
    notifications = data.get("notifications", {})
    
    update_data = {
        "notification_preferences": notifications,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    
    return {"success": True, "message": "Preferências atualizadas"}


@router.get("/preferences")
async def get_preferences(user: dict = Depends(get_current_user)):
    """
    Retorna as preferências de notificação do utilizador atual.
    """
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "notification_preferences": 1})
    
    notifications = user_data.get("notification_preferences", {}) if user_data else {}
    
    return {"notifications": notifications}


@router.put("/profile")
async def update_profile(
    data: dict,
    user: dict = Depends(get_current_user)
):
    """
    Permite ao utilizador atualizar o seu próprio perfil (nome e telefone).
    """
    from fastapi import HTTPException
    
    user_id = user["id"]
    
    # Campos permitidos para atualização pelo próprio utilizador
    allowed_fields = ["name", "phone"]
    update_data = {}
    
    for field in allowed_fields:
        if field in data and data[field] is not None:
            update_data[field] = data[field]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0 and result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    
    # Retornar o utilizador atualizado
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    
    return {
        "success": True,
        "message": "Perfil atualizado com sucesso",
        "user": updated_user
    }


@router.post("/change-password")
async def change_password(
    data: dict,
    user: dict = Depends(get_current_user)
):
    """
    Permite ao utilizador alterar a sua própria password.
    """
    from fastapi import HTTPException
    
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Password atual e nova password são obrigatórias")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="A nova password deve ter pelo menos 6 caracteres")
    
    # Buscar utilizador com password
    user_data = await db.users.find_one({"id": user["id"]})
    if not user_data:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    
    # Verificar password atual
    password_field = user_data.get("password") or user_data.get("hashed_password", "")
    if not verify_password(current_password, password_field):
        raise HTTPException(status_code=400, detail="Password atual incorreta")
    
    # Atualizar password
    new_hashed = hash_password(new_password)
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "password": new_hashed,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"success": True, "message": "Password alterada com sucesso"}
