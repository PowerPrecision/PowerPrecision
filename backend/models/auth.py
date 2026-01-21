from pydantic import BaseModel, EmailStr
from typing import Optional


class UserRole:
    CLIENTE = "cliente"
    CONSULTOR = "consultor"
    INTERMEDIARIO = "intermediario"  # Intermediário de Crédito (antes: mediador)
    MEDIADOR = "mediador"  # Legacy alias
    CONSULTOR_INTERMEDIARIO = "consultor_intermediario"  # Can do both consultor and intermediário tasks
    CONSULTOR_MEDIADOR = "consultor_mediador"  # Legacy alias
    CEO = "ceo"  # Between admin and staff - can manage basic things + consultor/intermediário tasks
    ADMIN = "admin"
    
    @classmethod
    def can_act_as_consultor(cls, role: str) -> bool:
        """Check if role can perform consultor tasks"""
        return role in [cls.CONSULTOR, cls.CONSULTOR_INTERMEDIARIO, cls.CONSULTOR_MEDIADOR, cls.CEO, cls.ADMIN]
    
    @classmethod
    def can_act_as_intermediario(cls, role: str) -> bool:
        """Check if role can perform intermediário de crédito tasks"""
        return role in [cls.INTERMEDIARIO, cls.MEDIADOR, cls.CONSULTOR_INTERMEDIARIO, cls.CONSULTOR_MEDIADOR, cls.CEO, cls.ADMIN]
    
    @classmethod
    def can_act_as_mediador(cls, role: str) -> bool:
        """Legacy alias for can_act_as_intermediario"""
        return cls.can_act_as_intermediario(role)
    
    @classmethod
    def is_staff(cls, role: str) -> bool:
        """Check if role is staff (not cliente)"""
        return role != cls.CLIENTE


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    phone: Optional[str] = None
    role: str
    is_active: Optional[bool] = True
    created_at: Optional[str] = None
    onedrive_folder: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    role: str
    onedrive_folder: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    onedrive_folder: Optional[str] = None
