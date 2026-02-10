from datetime import datetime
from app.core.database import db
from app.core.constants import TicketPriority

class SLA(db.Model):
    __tablename__ = "slas"

    id = db.Column(db.Integer, primary_key=True)
    priority = db.Column(db.Enum(TicketPriority), unique=True, nullable=False)
    response_time_hours = db.Column(db.Integer, nullable=False, default=24)
    resolution_time_hours = db.Column(db.Integer, nullable=False, default=72)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SLA {self.priority.value}>"
