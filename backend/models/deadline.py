from pydantic import BaseModel
from typing import Optional


class DeadlineCreate(BaseModel):
    process_id: Optional[str] = None  # Optional - can create general deadline
    title: str
    description: Optional[str] = None
    due_date: str
    priority: str = "medium"
    assigned_consultor_id: Optional[str] = None
    assigned_mediador_id: Optional[str] = None


class DeadlineUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    completed: Optional[bool] = None
    assigned_consultor_id: Optional[str] = None
    assigned_mediador_id: Optional[str] = None


class DeadlineResponse(BaseModel):
    id: str
    process_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    due_date: str
    priority: str
    completed: Optional[bool] = None  # Made optional to handle legacy data
    created_by: Optional[str] = None  # Made optional to handle legacy data
    created_at: str
    assigned_consultor_id: Optional[str] = None
    assigned_mediador_id: Optional[str] = None
    # Legacy fields from database
    status: Optional[str] = None
    assigned_user_id: Optional[str] = None
    assigned_user_name: Optional[str] = None
