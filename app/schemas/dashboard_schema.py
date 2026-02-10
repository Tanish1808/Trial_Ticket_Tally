from pydantic import BaseModel
from typing import Dict, List

class DashboardStats(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    pending_slas: int
    breached_slas: int

class AnalyticsResponse(BaseModel):
    stats: DashboardStats
    # Add more complex analytics fields as needed
