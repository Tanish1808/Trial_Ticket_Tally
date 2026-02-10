from datetime import datetime
from app.core.database import db
from app.core.constants import TicketStatus

class TicketStatusHistory(db.Model):
    __tablename__ = "ticket_status_history"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    
    old_status = db.Column(db.Enum(TicketStatus), nullable=True)
    new_status = db.Column(db.Enum(TicketStatus), nullable=False)
    
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    ticket = db.relationship("Ticket", back_populates="status_history")
    changed_by = db.relationship("User")

    def __repr__(self):
        return f"<History Ticket={self.ticket_id} {self.old_status}->{self.new_status}>"
