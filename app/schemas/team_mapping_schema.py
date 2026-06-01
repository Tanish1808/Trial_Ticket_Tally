from pydantic import BaseModel, Field
from typing import Optional

class TeamMappingCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=100, description="The category to route")
    team_id: int = Field(..., description="The target team ID")

class TeamMappingUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=100, description="The updated category name")
    team_id: Optional[int] = Field(None, description="The updated target team ID")
