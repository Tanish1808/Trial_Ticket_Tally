from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.constants import TicketStatus, TicketPriority
from app.schemas.auth_schema import UserResponse

class TicketCreate(BaseModel):
    title: str
    description: str
    category: str
    priority: TicketPriority = TicketPriority.MEDIUM
    team_id: Optional[int] = None # If creating for specific team

class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    status: Optional[TicketStatus] = None
    category: Optional[str] = None
    priority: Optional[TicketPriority] = None
    assigned_to_id: Optional[int] = None
    team_id: Optional[int] = None

class TicketResponse(BaseModel):
    id: int
    id: int
    title: str
    description: str
    category: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime
    created_by_id: int
    assigned_to_id: Optional[int]
    team_id: Optional[int]
    
    # Nested helpers might be needed for frontend, or just IDs
    creator: Optional[UserResponse] = None
    assignee: Optional[UserResponse] = None

    class Config:
        from_attributes = True
