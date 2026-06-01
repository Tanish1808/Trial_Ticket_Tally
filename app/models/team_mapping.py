from datetime import datetime
from app.core.database import db

class TeamMapping(db.Model):
    __tablename__ = "team_mappings"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), unique=True, nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Team
    team = db.relationship("Team", backref=db.backref("mappings", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<TeamMapping {self.category} -> {self.team.name if self.team else self.team_id}>"
