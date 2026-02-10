from pydantic import BaseModel
from typing import List, Optional

class TeamCreate(BaseModel):
    name: str

class TeamResponse(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True
