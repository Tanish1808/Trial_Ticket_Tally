from app.utils.time_utils import utcnow
from app.core.database import db

class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationship to User (admin creator)
    creator = db.relationship("User", backref=db.backref("announcements", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "created_by": self.creator.full_name if self.creator else "System"
        }
