from datetime import datetime
from app.core.database import db
from app.core.constants import UserRole

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    department = db.Column(db.String(100), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    preferences = db.Column(db.JSON, default={})

    # Relationships
    team = db.relationship("Team", back_populates="members")
    created_tickets = db.relationship("Ticket", foreign_keys="[Ticket.created_by_id]", back_populates="creator")
    assigned_tickets = db.relationship("Ticket", foreign_keys="[Ticket.assigned_to_id]", back_populates="assignee")

    def __repr__(self):
        return f"<User {self.email} - {self.role.value}>"
