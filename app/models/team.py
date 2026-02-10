from datetime import datetime
from app.core.database import db

class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    members = db.relationship("User", back_populates="team")
    tickets = db.relationship("Ticket", back_populates="team")

    def __repr__(self):
        return f"<Team {self.name}>"
