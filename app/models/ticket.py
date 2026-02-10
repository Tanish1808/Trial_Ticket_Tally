from datetime import datetime
from app.core.database import db
from app.core.constants import TicketStatus, TicketPriority

class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default="General")
    status = db.Column(db.Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = db.Column(db.Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = db.relationship("User", foreign_keys=[created_by_id], back_populates="created_tickets")
    assignee = db.relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_tickets")
    team = db.relationship("Team", back_populates="tickets")
    status_history = db.relationship("TicketStatusHistory", back_populates="ticket", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="ticket", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Ticket {self.id} - {self.title}>"
