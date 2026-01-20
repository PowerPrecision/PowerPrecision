from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'super-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# OneDrive Config
ONEDRIVE_TENANT_ID = os.environ.get('ONEDRIVE_TENANT_ID', '')
ONEDRIVE_CLIENT_ID = os.environ.get('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_CLIENT_SECRET = os.environ.get('ONEDRIVE_CLIENT_SECRET', '')
ONEDRIVE_BASE_PATH = os.environ.get('ONEDRIVE_BASE_PATH', 'Documentação Clientes')

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============== MODELS ==============

class UserRole:
    CLIENTE = "cliente"
    CONSULTOR = "consultor"
    MEDIADOR = "mediador"
    ADMIN = "admin"

class ProcessType:
    CREDITO = "credito"
    IMOBILIARIA = "imobiliaria"
    AMBOS = "ambos"

# Auth Models
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
    created_at: str
    onedrive_folder: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Process Models
class PersonalData(BaseModel):
    nif: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None

class FinancialData(BaseModel):
    monthly_income: Optional[float] = None
    other_income: Optional[float] = None
    monthly_expenses: Optional[float] = None
    employment_type: Optional[str] = None
    employer_name: Optional[str] = None
    employment_duration: Optional[str] = None
    has_debts: Optional[bool] = None
    debt_amount: Optional[float] = None

class RealEstateData(BaseModel):
    property_type: Optional[str] = None
    property_zone: Optional[str] = None
    desired_area: Optional[float] = None
    max_budget: Optional[float] = None
    property_purpose: Optional[str] = None
    notes: Optional[str] = None

class CreditData(BaseModel):
    requested_amount: Optional[float] = None
    loan_term_years: Optional[int] = None
    interest_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    bank_name: Optional[str] = None
    bank_approval_date: Optional[str] = None
    bank_approval_notes: Optional[str] = None

class ProcessCreate(BaseModel):
    process_type: str
    personal_data: Optional[PersonalData] = None
    financial_data: Optional[FinancialData] = None

class ProcessUpdate(BaseModel):
    personal_data: Optional[PersonalData] = None
    financial_data: Optional[FinancialData] = None
    real_estate_data: Optional[RealEstateData] = None
    credit_data: Optional[CreditData] = None
    status: Optional[str] = None

class ProcessResponse(BaseModel):
    id: str
    client_id: str
    client_name: str
    client_email: str
    process_type: str
    status: str
    personal_data: Optional[dict] = None
    financial_data: Optional[dict] = None
    real_estate_data: Optional[dict] = None
    credit_data: Optional[dict] = None
    assigned_consultor_id: Optional[str] = None
    assigned_mediador_id: Optional[str] = None
    created_at: str
    updated_at: str

# Deadline Models
class DeadlineCreate(BaseModel):
    process_id: str
    title: str
    description: Optional[str] = None
    due_date: str
    priority: str = "medium"

class DeadlineUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    completed: Optional[bool] = None

class DeadlineResponse(BaseModel):
    id: str
    process_id: str
    title: str
    description: Optional[str] = None
    due_date: str
    priority: str
    completed: bool
    created_by: str
    created_at: str

# User Management Models
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

# Activity/Comments Models
class ActivityCreate(BaseModel):
    process_id: str
    comment: str

class ActivityResponse(BaseModel):
    id: str
    process_id: str
    user_id: str
    user_name: str
    user_role: str
    comment: str
    created_at: str

# History Models
class HistoryResponse(BaseModel):
    id: str
    process_id: str
    user_id: str
    user_name: str
    action: str
    field: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    created_at: str

# Workflow/Status Models
class WorkflowStatusCreate(BaseModel):
    name: str
    label: str
    order: int
    color: str = "blue"
    description: Optional[str] = None

class WorkflowStatusUpdate(BaseModel):
    label: Optional[str] = None
    order: Optional[int] = None
    color: Optional[str] = None
    description: Optional[str] = None

class WorkflowStatusResponse(BaseModel):
    id: str
    name: str
    label: str
    order: int
    color: str
    description: Optional[str] = None
    is_default: bool = False

# OneDrive Models
class OneDriveFile(BaseModel):
    id: str
    name: str
    size: Optional[int] = None
    is_folder: bool
    modified_at: Optional[str] = None
    web_url: Optional[str] = None
    download_url: Optional[str] = None

# ============== AUTH HELPERS ==============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Utilizador não encontrado")
        if not user.get("is_active", True):
            raise HTTPException(status_code=401, detail="Conta desativada")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

def require_roles(allowed_roles: List[str]):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permissão negada")
        return user
    return role_checker

# ============== HISTORY HELPER ==============

async def log_history(process_id: str, user: dict, action: str, field: str = None, old_value: Any = None, new_value: Any = None):
    """Log a change to process history"""
    history_doc = {
        "id": str(uuid.uuid4()),
        "process_id": process_id,
        "user_id": user["id"],
        "user_name": user["name"],
        "action": action,
        "field": field,
        "old_value": str(old_value) if old_value is not None else None,
        "new_value": str(new_value) if new_value is not None else None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.history.insert_one(history_doc)

async def log_data_changes(process_id: str, user: dict, old_data: dict, new_data: dict, section: str):
    """Compare and log changes between old and new data"""
    if old_data is None:
        old_data = {}
    if new_data is None:
        return
    
    for key, new_val in new_data.items():
        old_val = old_data.get(key)
        if old_val != new_val and new_val is not None:
            await log_history(
                process_id, user, 
                f"Alterou {section}", 
                key, old_val, new_val
            )

# ============== EMAIL SERVICE (MOCK) ==============

async def send_email_notification(to_email: str, subject: str, body: str):
    """Mock email service - logs instead of sending"""
    logger.info(f"📧 EMAIL NOTIFICATION")
    logger.info(f"   To: {to_email}")
    logger.info(f"   Subject: {subject}")
    logger.info(f"   Body: {body[:100]}...")
    await db.email_logs.insert_one({
        "id": str(uuid.uuid4()),
        "to": to_email,
        "subject": subject,
        "body": body,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "simulated"
    })
    return True

# ============== ONEDRIVE SERVICE ==============

class OneDriveService:
    def __init__(self):
        self.token = None
        self.token_expires = None
    
    async def get_access_token(self) -> str:
        """Get Microsoft Graph access token using client credentials"""
        if not all([ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET]):
            raise HTTPException(status_code=503, detail="OneDrive não configurado. Configure as variáveis ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID e ONEDRIVE_CLIENT_SECRET.")
        
        if self.token and self.token_expires and datetime.now(timezone.utc) < self.token_expires:
            return self.token
        
        token_url = f"https://login.microsoftonline.com/{ONEDRIVE_TENANT_ID}/oauth2/v2.0/token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data={
                "client_id": ONEDRIVE_CLIENT_ID,
                "client_secret": ONEDRIVE_CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            })
            
            if response.status_code != 200:
                logger.error(f"OneDrive auth failed: {response.text}")
                raise HTTPException(status_code=503, detail="Erro de autenticação OneDrive")
            
            data = response.json()
            self.token = data["access_token"]
            self.token_expires = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"] - 60)
            return self.token
    
    async def list_files(self, folder_path: str) -> List[OneDriveFile]:
        """List files in a OneDrive folder"""
        token = await self.get_access_token()
        
        # Encode path for URL
        encoded_path = folder_path.replace(" ", "%20")
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_path}:/children"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            
            if response.status_code == 404:
                return []
            
            if response.status_code != 200:
                logger.error(f"OneDrive list failed: {response.text}")
                raise HTTPException(status_code=503, detail="Erro ao listar ficheiros do OneDrive")
            
            data = response.json()
            files = []
            
            for item in data.get("value", []):
                files.append(OneDriveFile(
                    id=item["id"],
                    name=item["name"],
                    size=item.get("size"),
                    is_folder="folder" in item,
                    modified_at=item.get("lastModifiedDateTime"),
                    web_url=item.get("webUrl"),
                    download_url=item.get("@microsoft.graph.downloadUrl")
                ))
            
            return files
    
    async def get_download_url(self, item_id: str) -> str:
        """Get download URL for a file"""
        token = await self.get_access_token()
        
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Ficheiro não encontrado")
            
            data = response.json()
            return data.get("@microsoft.graph.downloadUrl", data.get("webUrl"))

onedrive_service = OneDriveService()

# ============== AUTH ROUTES ==============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(data: UserRegister):
    existing = await db.users.find_one({"email": data.email})
    if existing:
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
        "onedrive_folder": data.name,  # Default folder name = user name
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

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not verify_password(data.password, user["password"]):
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

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        phone=user.get("phone"),
        role=user["role"],
        created_at=user["created_at"],
        onedrive_folder=user.get("onedrive_folder")
    )

# ============== WORKFLOW STATUS ROUTES (ADMIN) ==============

@api_router.get("/workflow-statuses", response_model=List[WorkflowStatusResponse])
async def get_workflow_statuses(user: dict = Depends(get_current_user)):
    """Get all workflow statuses ordered by order field"""
    statuses = await db.workflow_statuses.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return [WorkflowStatusResponse(**s) for s in statuses]

@api_router.post("/workflow-statuses", response_model=WorkflowStatusResponse)
async def create_workflow_status(data: WorkflowStatusCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a new workflow status"""
    existing = await db.workflow_statuses.find_one({"name": data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Estado já existe")
    
    status_doc = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "label": data.label,
        "order": data.order,
        "color": data.color,
        "description": data.description,
        "is_default": False
    }
    
    await db.workflow_statuses.insert_one(status_doc)
    return WorkflowStatusResponse(**{k: v for k, v in status_doc.items() if k != "_id"})

@api_router.put("/workflow-statuses/{status_id}", response_model=WorkflowStatusResponse)
async def update_workflow_status(status_id: str, data: WorkflowStatusUpdate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Update a workflow status"""
    status = await db.workflow_statuses.find_one({"id": status_id}, {"_id": 0})
    if not status:
        raise HTTPException(status_code=404, detail="Estado não encontrado")
    
    update_data = {}
    if data.label is not None:
        update_data["label"] = data.label
    if data.order is not None:
        update_data["order"] = data.order
    if data.color is not None:
        update_data["color"] = data.color
    if data.description is not None:
        update_data["description"] = data.description
    
    if update_data:
        await db.workflow_statuses.update_one({"id": status_id}, {"$set": update_data})
    
    updated = await db.workflow_statuses.find_one({"id": status_id}, {"_id": 0})
    return WorkflowStatusResponse(**updated)

@api_router.delete("/workflow-statuses/{status_id}")
async def delete_workflow_status(status_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Delete a workflow status"""
    status = await db.workflow_statuses.find_one({"id": status_id})
    if not status:
        raise HTTPException(status_code=404, detail="Estado não encontrado")
    
    if status.get("is_default"):
        raise HTTPException(status_code=400, detail="Não pode eliminar estados padrão")
    
    # Check if any process uses this status
    process_count = await db.processes.count_documents({"status": status["name"]})
    if process_count > 0:
        raise HTTPException(status_code=400, detail=f"Existem {process_count} processos com este estado")
    
    await db.workflow_statuses.delete_one({"id": status_id})
    return {"message": "Estado eliminado"}

# ============== PROCESS ROUTES ==============

@api_router.post("/processes", response_model=ProcessResponse)
async def create_process(data: ProcessCreate, user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.CLIENTE:
        raise HTTPException(status_code=403, detail="Apenas clientes podem criar processos")
    
    # Get first workflow status
    first_status = await db.workflow_statuses.find_one({}, {"_id": 0}, sort=[("order", 1)])
    initial_status = first_status["name"] if first_status else "pedido_inicial"
    
    process_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    process_doc = {
        "id": process_id,
        "client_id": user["id"],
        "client_name": user["name"],
        "client_email": user["email"],
        "process_type": data.process_type,
        "status": initial_status,
        "personal_data": data.personal_data.model_dump() if data.personal_data else None,
        "financial_data": data.financial_data.model_dump() if data.financial_data else None,
        "real_estate_data": None,
        "credit_data": None,
        "assigned_consultor_id": None,
        "assigned_mediador_id": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.processes.insert_one(process_doc)
    
    # Log history
    await log_history(process_id, user, "Criou processo")
    
    # Notify admins
    admins = await db.users.find({"role": UserRole.ADMIN}, {"_id": 0}).to_list(100)
    for admin in admins:
        await send_email_notification(
            admin["email"],
            "Novo Processo Criado",
            f"O cliente {user['name']} criou um novo processo de {data.process_type}."
        )
    
    return ProcessResponse(**{k: v for k, v in process_doc.items() if k != "_id"})

@api_router.get("/processes", response_model=List[ProcessResponse])
async def get_processes(user: dict = Depends(get_current_user)):
    query = {}
    
    if user["role"] == UserRole.CLIENTE:
        query["client_id"] = user["id"]
    elif user["role"] == UserRole.CONSULTOR:
        query["$or"] = [
            {"assigned_consultor_id": user["id"]},
            {"assigned_consultor_id": None, "process_type": {"$in": [ProcessType.IMOBILIARIA, ProcessType.AMBOS]}}
        ]
    elif user["role"] == UserRole.MEDIADOR:
        query["$or"] = [
            {"assigned_mediador_id": user["id"]},
            {"assigned_mediador_id": None, "process_type": {"$in": [ProcessType.CREDITO, ProcessType.AMBOS]}}
        ]
    
    processes = await db.processes.find(query, {"_id": 0}).to_list(1000)
    return [ProcessResponse(**p) for p in processes]

@api_router.get("/processes/{process_id}", response_model=ProcessResponse)
async def get_process(process_id: str, user: dict = Depends(get_current_user)):
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    if user["role"] == UserRole.CLIENTE and process["client_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    return ProcessResponse(**process)

@api_router.put("/processes/{process_id}", response_model=ProcessResponse)
async def update_process(process_id: str, data: ProcessUpdate, user: dict = Depends(get_current_user)):
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    # Get valid statuses
    valid_statuses = [s["name"] for s in await db.workflow_statuses.find({}, {"name": 1, "_id": 0}).to_list(100)]
    
    if user["role"] == UserRole.CLIENTE:
        if process["client_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Acesso negado")
        if data.personal_data:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        if data.financial_data:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
    
    elif user["role"] == UserRole.CONSULTOR:
        if data.personal_data:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        if data.financial_data:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
        if data.real_estate_data:
            await log_data_changes(process_id, user, process.get("real_estate_data"), data.real_estate_data.model_dump(), "dados imobiliários")
            update_data["real_estate_data"] = data.real_estate_data.model_dump()
        if data.status and (data.status in valid_statuses or not valid_statuses):
            await log_history(process_id, user, "Alterou estado", "status", process["status"], data.status)
            update_data["status"] = data.status
        if not process.get("assigned_consultor_id"):
            update_data["assigned_consultor_id"] = user["id"]
    
    elif user["role"] == UserRole.MEDIADOR:
        if data.personal_data:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        if data.financial_data:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
        if data.credit_data:
            # Check if status allows credit data
            credit_statuses = await db.workflow_statuses.find({"order": {"$gte": 3}}, {"name": 1, "_id": 0}).to_list(100)
            allowed_statuses = [s["name"] for s in credit_statuses] if credit_statuses else ["autorizacao_bancaria", "aprovado"]
            if process["status"] not in allowed_statuses:
                raise HTTPException(status_code=400, detail="Dados de crédito só podem ser adicionados após autorização bancária")
            await log_data_changes(process_id, user, process.get("credit_data"), data.credit_data.model_dump(), "dados de crédito")
            update_data["credit_data"] = data.credit_data.model_dump()
        if data.status and (data.status in valid_statuses or not valid_statuses):
            await log_history(process_id, user, "Alterou estado", "status", process["status"], data.status)
            update_data["status"] = data.status
            await send_email_notification(
                process["client_email"],
                f"Estado do Processo Atualizado",
                f"O estado do seu processo foi atualizado para: {data.status}"
            )
        if not process.get("assigned_mediador_id"):
            update_data["assigned_mediador_id"] = user["id"]
    
    elif user["role"] == UserRole.ADMIN:
        if data.personal_data:
            await log_data_changes(process_id, user, process.get("personal_data"), data.personal_data.model_dump(), "dados pessoais")
            update_data["personal_data"] = data.personal_data.model_dump()
        if data.financial_data:
            await log_data_changes(process_id, user, process.get("financial_data"), data.financial_data.model_dump(), "dados financeiros")
            update_data["financial_data"] = data.financial_data.model_dump()
        if data.real_estate_data:
            await log_data_changes(process_id, user, process.get("real_estate_data"), data.real_estate_data.model_dump(), "dados imobiliários")
            update_data["real_estate_data"] = data.real_estate_data.model_dump()
        if data.credit_data:
            await log_data_changes(process_id, user, process.get("credit_data"), data.credit_data.model_dump(), "dados de crédito")
            update_data["credit_data"] = data.credit_data.model_dump()
        if data.status:
            await log_history(process_id, user, "Alterou estado", "status", process["status"], data.status)
            update_data["status"] = data.status
    
    await db.processes.update_one({"id": process_id}, {"$set": update_data})
    updated = await db.processes.find_one({"id": process_id}, {"_id": 0})
    
    return ProcessResponse(**updated)

@api_router.post("/processes/{process_id}/assign")
async def assign_process(
    process_id: str, 
    consultor_id: Optional[str] = None,
    mediador_id: Optional[str] = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    process = await db.processes.find_one({"id": process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if consultor_id:
        consultor = await db.users.find_one({"id": consultor_id, "role": UserRole.CONSULTOR})
        if not consultor:
            raise HTTPException(status_code=404, detail="Consultor não encontrado")
        update_data["assigned_consultor_id"] = consultor_id
        await log_history(process_id, user, "Atribuiu consultor", "assigned_consultor_id", None, consultor["name"])
    
    if mediador_id:
        mediador = await db.users.find_one({"id": mediador_id, "role": UserRole.MEDIADOR})
        if not mediador:
            raise HTTPException(status_code=404, detail="Mediador não encontrado")
        update_data["assigned_mediador_id"] = mediador_id
        await log_history(process_id, user, "Atribuiu mediador", "assigned_mediador_id", None, mediador["name"])
    
    await db.processes.update_one({"id": process_id}, {"$set": update_data})
    return {"message": "Processo atribuído com sucesso"}

# ============== ACTIVITY/COMMENTS ROUTES ==============

@api_router.post("/activities", response_model=ActivityResponse)
async def create_activity(data: ActivityCreate, user: dict = Depends(get_current_user)):
    """Create a new activity/comment on a process"""
    process = await db.processes.find_one({"id": data.process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Check access
    if user["role"] == UserRole.CLIENTE and process["client_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    activity_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    activity_doc = {
        "id": activity_id,
        "process_id": data.process_id,
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user["role"],
        "comment": data.comment,
        "created_at": now
    }
    
    await db.activities.insert_one(activity_doc)
    
    # Log to history
    await log_history(data.process_id, user, "Adicionou comentário")
    
    return ActivityResponse(**{k: v for k, v in activity_doc.items() if k != "_id"})

@api_router.get("/activities", response_model=List[ActivityResponse])
async def get_activities(process_id: str, user: dict = Depends(get_current_user)):
    """Get all activities for a process"""
    process = await db.processes.find_one({"id": process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Check access
    if user["role"] == UserRole.CLIENTE and process["client_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    activities = await db.activities.find({"process_id": process_id}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [ActivityResponse(**a) for a in activities]

@api_router.delete("/activities/{activity_id}")
async def delete_activity(activity_id: str, user: dict = Depends(get_current_user)):
    """Delete an activity (only owner or admin)"""
    activity = await db.activities.find_one({"id": activity_id})
    if not activity:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    
    if activity["user_id"] != user["id"] and user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Só pode eliminar os seus próprios comentários")
    
    await db.activities.delete_one({"id": activity_id})
    return {"message": "Comentário eliminado"}

# ============== HISTORY ROUTES ==============

@api_router.get("/history", response_model=List[HistoryResponse])
async def get_history(process_id: str, user: dict = Depends(get_current_user)):
    """Get history for a process"""
    process = await db.processes.find_one({"id": process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Check access
    if user["role"] == UserRole.CLIENTE and process["client_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    history = await db.history.find({"process_id": process_id}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [HistoryResponse(**h) for h in history]

# ============== DEADLINE ROUTES ==============

@api_router.post("/deadlines", response_model=DeadlineResponse)
async def create_deadline(data: DeadlineCreate, user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.CLIENTE:
        raise HTTPException(status_code=403, detail="Clientes não podem criar prazos")
    
    process = await db.processes.find_one({"id": data.process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    deadline_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    deadline_doc = {
        "id": deadline_id,
        "process_id": data.process_id,
        "title": data.title,
        "description": data.description,
        "due_date": data.due_date,
        "priority": data.priority,
        "completed": False,
        "created_by": user["id"],
        "created_at": now
    }
    
    await db.deadlines.insert_one(deadline_doc)
    await log_history(data.process_id, user, "Criou prazo", "deadline", None, data.title)
    
    await send_email_notification(
        process["client_email"],
        f"Novo Prazo: {data.title}",
        f"Foi adicionado um novo prazo ao seu processo: {data.title} - Data limite: {data.due_date}"
    )
    
    return DeadlineResponse(**{k: v for k, v in deadline_doc.items() if k != "_id"})

@api_router.get("/deadlines", response_model=List[DeadlineResponse])
async def get_deadlines(process_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    
    if process_id:
        query["process_id"] = process_id
    elif user["role"] == UserRole.CLIENTE:
        processes = await db.processes.find({"client_id": user["id"]}, {"id": 1, "_id": 0}).to_list(1000)
        process_ids = [p["id"] for p in processes]
        query["process_id"] = {"$in": process_ids}
    
    deadlines = await db.deadlines.find(query, {"_id": 0}).to_list(1000)
    return [DeadlineResponse(**d) for d in deadlines]

@api_router.put("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(deadline_id: str, data: DeadlineUpdate, user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.CLIENTE:
        raise HTTPException(status_code=403, detail="Clientes não podem editar prazos")
    
    deadline = await db.deadlines.find_one({"id": deadline_id}, {"_id": 0})
    if not deadline:
        raise HTTPException(status_code=404, detail="Prazo não encontrado")
    
    update_data = {}
    if data.title is not None:
        update_data["title"] = data.title
    if data.description is not None:
        update_data["description"] = data.description
    if data.due_date is not None:
        update_data["due_date"] = data.due_date
    if data.priority is not None:
        update_data["priority"] = data.priority
    if data.completed is not None:
        update_data["completed"] = data.completed
        if data.completed:
            await log_history(deadline["process_id"], user, "Concluiu prazo", "deadline", deadline["title"], "concluído")
    
    if update_data:
        await db.deadlines.update_one({"id": deadline_id}, {"$set": update_data})
    
    updated = await db.deadlines.find_one({"id": deadline_id}, {"_id": 0})
    return DeadlineResponse(**updated)

@api_router.delete("/deadlines/{deadline_id}")
async def delete_deadline(deadline_id: str, user: dict = Depends(require_roles([UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.ADMIN]))):
    result = await db.deadlines.delete_one({"id": deadline_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Prazo não encontrado")
    return {"message": "Prazo eliminado"}

# ============== USER MANAGEMENT (ADMIN) ==============

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(role: Optional[str] = None, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    query = {}
    if role:
        query["role"] = role
    
    users = await db.users.find(query, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

@api_router.post("/users", response_model=UserResponse)
async def create_user(data: UserCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já registado")
    
    if data.role not in [UserRole.CLIENTE, UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.ADMIN]:
        raise HTTPException(status_code=400, detail="Role inválido")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password": hash_password(data.password),
        "name": data.name,
        "phone": data.phone,
        "role": data.role,
        "is_active": True,
        "onedrive_folder": data.onedrive_folder or data.name,
        "created_at": now
    }
    
    await db.users.insert_one(user_doc)
    
    return UserResponse(
        id=user_id,
        email=data.email,
        name=data.name,
        phone=data.phone,
        role=data.role,
        created_at=now,
        onedrive_folder=data.onedrive_folder or data.name
    )

@api_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, data: UserUpdate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.phone is not None:
        update_data["phone"] = data.phone
    if data.role is not None:
        if data.role not in [UserRole.CLIENTE, UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.ADMIN]:
            raise HTTPException(status_code=400, detail="Role inválido")
        update_data["role"] = data.role
    if data.is_active is not None:
        update_data["is_active"] = data.is_active
    if data.onedrive_folder is not None:
        update_data["onedrive_folder"] = data.onedrive_folder
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return UserResponse(**updated)

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Não pode eliminar a própria conta")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    return {"message": "Utilizador eliminado"}

# ============== ONEDRIVE ROUTES ==============

@api_router.get("/onedrive/files", response_model=List[OneDriveFile])
async def list_onedrive_files(
    folder: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List files from OneDrive for the current user"""
    # Determine folder path based on user role
    if user["role"] == UserRole.CLIENTE:
        # Clients can only see their own folder
        user_folder = user.get("onedrive_folder", user["name"])
        folder_path = f"{ONEDRIVE_BASE_PATH}/{user_folder}"
        if folder:
            folder_path = f"{folder_path}/{folder}"
    else:
        # Consultors, mediadors and admins can see all client folders
        if folder:
            folder_path = f"{ONEDRIVE_BASE_PATH}/{folder}"
        else:
            folder_path = ONEDRIVE_BASE_PATH
    
    try:
        files = await onedrive_service.list_files(folder_path)
        return files
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OneDrive error: {e}")
        raise HTTPException(status_code=503, detail="Erro ao aceder ao OneDrive")

@api_router.get("/onedrive/files/{client_name}", response_model=List[OneDriveFile])
async def list_client_onedrive_files(
    client_name: str,
    subfolder: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List files from a specific client's OneDrive folder"""
    # Clients can only see their own folder
    if user["role"] == UserRole.CLIENTE:
        user_folder = user.get("onedrive_folder", user["name"])
        if client_name != user_folder:
            raise HTTPException(status_code=403, detail="Acesso negado")
    
    folder_path = f"{ONEDRIVE_BASE_PATH}/{client_name}"
    if subfolder:
        folder_path = f"{folder_path}/{subfolder}"
    
    try:
        files = await onedrive_service.list_files(folder_path)
        return files
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OneDrive error: {e}")
        raise HTTPException(status_code=503, detail="Erro ao aceder ao OneDrive")

@api_router.get("/onedrive/download/{item_id}")
async def get_onedrive_download_url(item_id: str, user: dict = Depends(get_current_user)):
    """Get download URL for a OneDrive file"""
    try:
        download_url = await onedrive_service.get_download_url(item_id)
        return {"download_url": download_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OneDrive download error: {e}")
        raise HTTPException(status_code=503, detail="Erro ao obter link de download")

@api_router.get("/onedrive/status")
async def get_onedrive_status(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Check OneDrive integration status"""
    configured = all([ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET])
    return {
        "configured": configured,
        "tenant_id": ONEDRIVE_TENANT_ID[:8] + "..." if ONEDRIVE_TENANT_ID else None,
        "client_id": ONEDRIVE_CLIENT_ID[:8] + "..." if ONEDRIVE_CLIENT_ID else None,
        "base_path": ONEDRIVE_BASE_PATH
    }

# ============== STATS ==============

@api_router.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    stats = {}
    
    # Get workflow statuses for dynamic stats
    statuses = await db.workflow_statuses.find({}, {"_id": 0}).to_list(100)
    
    if user["role"] == UserRole.CLIENTE:
        stats["total_processes"] = await db.processes.count_documents({"client_id": user["id"]})
        stats["pending_deadlines"] = await db.deadlines.count_documents({
            "process_id": {"$in": [p["id"] for p in await db.processes.find({"client_id": user["id"]}, {"id": 1}).to_list(100)]},
            "completed": False
        })
    elif user["role"] in [UserRole.CONSULTOR, UserRole.MEDIADOR, UserRole.ADMIN]:
        stats["total_processes"] = await db.processes.count_documents({})
        
        # Count by each status
        for status in statuses:
            stats[f"status_{status['name']}"] = await db.processes.count_documents({"status": status["name"]})
        
        # Fallback for default statuses if no custom ones
        if not statuses:
            stats["pending_processes"] = await db.processes.count_documents({"status": "pedido_inicial"})
            stats["in_analysis"] = await db.processes.count_documents({"status": "em_analise"})
            stats["bank_authorization"] = await db.processes.count_documents({"status": "autorizacao_bancaria"})
            stats["approved"] = await db.processes.count_documents({"status": "aprovado"})
            stats["rejected"] = await db.processes.count_documents({"status": "rejeitado"})
        
        stats["total_deadlines"] = await db.deadlines.count_documents({})
        stats["pending_deadlines"] = await db.deadlines.count_documents({"completed": False})
    
    if user["role"] == UserRole.ADMIN:
        stats["total_users"] = await db.users.count_documents({})
        stats["clients"] = await db.users.count_documents({"role": UserRole.CLIENTE})
        stats["consultors"] = await db.users.count_documents({"role": UserRole.CONSULTOR})
        stats["mediadors"] = await db.users.count_documents({"role": UserRole.MEDIADOR})
    
    return stats

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.processes.create_index("id", unique=True)
    await db.processes.create_index("client_id")
    await db.deadlines.create_index("id", unique=True)
    await db.deadlines.create_index("process_id")
    await db.activities.create_index("process_id")
    await db.history.create_index("process_id")
    await db.workflow_statuses.create_index("name", unique=True)
    
    # Create default workflow statuses if none exist
    status_count = await db.workflow_statuses.count_documents({})
    if status_count == 0:
        default_statuses = [
            {"id": str(uuid.uuid4()), "name": "pedido_inicial", "label": "Pedido Inicial", "order": 1, "color": "yellow", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "em_analise", "label": "Em Análise", "order": 2, "color": "blue", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "autorizacao_bancaria", "label": "Autorização Bancária", "order": 3, "color": "orange", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "aprovado", "label": "Aprovado", "order": 4, "color": "green", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "rejeitado", "label": "Rejeitado", "order": 5, "color": "red", "is_default": True},
        ]
        await db.workflow_statuses.insert_many(default_statuses)
        logger.info("Default workflow statuses created")
    
    # Create default admin if not exists
    admin_exists = await db.users.find_one({"role": UserRole.ADMIN})
    if not admin_exists:
        admin_doc = {
            "id": str(uuid.uuid4()),
            "email": "admin@sistema.pt",
            "password": hash_password("admin123"),
            "name": "Administrador",
            "phone": None,
            "role": UserRole.ADMIN,
            "is_active": True,
            "onedrive_folder": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_doc)
        logger.info("Admin user created: admin@sistema.pt / admin123")
    
    # Create test clients if none exist
    client_count = await db.users.count_documents({"role": UserRole.CLIENTE})
    if client_count == 0:
        test_clients = [
            {"name": "João Silva", "email": "joao.silva@email.pt", "phone": "+351 912 345 678", "onedrive_folder": "João Silva"},
            {"name": "Maria Santos", "email": "maria.santos@email.pt", "phone": "+351 923 456 789", "onedrive_folder": "Maria Santos"},
            {"name": "Pedro Costa", "email": "pedro.costa@email.pt", "phone": "+351 934 567 890", "onedrive_folder": "Pedro Costa"},
        ]
        for client in test_clients:
            client_doc = {
                "id": str(uuid.uuid4()),
                "email": client["email"],
                "password": hash_password("cliente123"),
                "name": client["name"],
                "phone": client["phone"],
                "role": UserRole.CLIENTE,
                "is_active": True,
                "onedrive_folder": client["onedrive_folder"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(client_doc)
        logger.info("Test clients created (password: cliente123)")
    
    # Create test consultor and mediador if none exist
    consultor_exists = await db.users.find_one({"role": UserRole.CONSULTOR})
    if not consultor_exists:
        consultor_doc = {
            "id": str(uuid.uuid4()),
            "email": "consultor@sistema.pt",
            "password": hash_password("consultor123"),
            "name": "Carlos Consultor",
            "phone": "+351 961 234 567",
            "role": UserRole.CONSULTOR,
            "is_active": True,
            "onedrive_folder": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(consultor_doc)
        logger.info("Test consultor created: consultor@sistema.pt / consultor123")
    
    mediador_exists = await db.users.find_one({"role": UserRole.MEDIADOR})
    if not mediador_exists:
        mediador_doc = {
            "id": str(uuid.uuid4()),
            "email": "mediador@sistema.pt",
            "password": hash_password("mediador123"),
            "name": "Ana Mediadora",
            "phone": "+351 962 345 678",
            "role": UserRole.MEDIADOR,
            "is_active": True,
            "onedrive_folder": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(mediador_doc)
        logger.info("Test mediador created: mediador@sistema.pt / mediador123")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
