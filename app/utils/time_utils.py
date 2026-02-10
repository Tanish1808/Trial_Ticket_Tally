from datetime import datetime, timedelta

def calculate_sla_deadline(start_time: datetime, hours: int) -> datetime:
    """
    Calculates the deadline based on start time and SLA hours.
    TODO: Add business hours logic if needed.
    """
    return start_time + timedelta(hours=hours)

def is_breached(deadline: datetime) -> bool:
    return datetime.utcnow() > deadline
