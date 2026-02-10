from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.constants import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    department: Optional[str] = None
    role: Optional[UserRole] = UserRole.EMPLOYEE
    team_id: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    team_id: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
