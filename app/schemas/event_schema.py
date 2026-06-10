from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional

def convert_to_naive_utc(v: datetime) -> datetime:
    if v is not None and v.tzinfo is not None:
        return v.astimezone(timezone.utc).replace(tzinfo=None)
    return v

class EventCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None)
    event_type: str = Field("maintenance", min_length=2, max_length=50)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)

    @field_validator('start_time', 'end_time')
    @classmethod
    def ensure_naive_utc(cls, v: datetime) -> datetime:
        return convert_to_naive_utc(v)

class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None)
    event_type: Optional[str] = Field(None, min_length=2, max_length=50)
    start_time: Optional[datetime] = Field(None)
    end_time: Optional[datetime] = Field(None)

    @field_validator('start_time', 'end_time')
    @classmethod
    def ensure_naive_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return convert_to_naive_utc(v) if v is not None else None
