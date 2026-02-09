import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request

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
@limiter.limit("3/hour")  # Limite restritivo: 3 registos por hora por IP
async def register(request: Request, data: UserRegister):
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
@limiter.limit("5/minute")
async def login(request: Request, data: UserLogin):
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
