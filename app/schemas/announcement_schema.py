from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="The title of the announcement")
    message: str = Field(..., min_length=5, description="The message details of the announcement")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date/time")

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    message: Optional[str] = Field(None, min_length=5)
    is_active: Optional[bool] = Field(None)
    expires_at: Optional[datetime] = Field(None)
