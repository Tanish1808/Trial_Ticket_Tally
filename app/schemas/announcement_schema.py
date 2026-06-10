from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional

def convert_to_naive_utc(v: Optional[datetime]) -> Optional[datetime]:
    if v is not None and v.tzinfo is not None:
        return v.astimezone(timezone.utc).replace(tzinfo=None)
    return v

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="The title of the announcement")
    message: str = Field(..., min_length=5, description="The message details of the announcement")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date/time")

    @field_validator('expires_at')
    @classmethod
    def ensure_naive_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return convert_to_naive_utc(v)

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    message: Optional[str] = Field(None, min_length=5)
    is_active: Optional[bool] = Field(None)
    expires_at: Optional[datetime] = Field(None)

    @field_validator('expires_at')
    @classmethod
    def ensure_naive_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return convert_to_naive_utc(v)
