from pydantic import BaseModel, Field
from typing import Optional

class CSATFeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="CSAT Rating from 1 to 5")
    comment: Optional[str] = Field(None, description="Optional text comment feedback")
