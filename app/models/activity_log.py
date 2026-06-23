from app.utils.time_utils import utcnow
from app.core.database import db

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) # 'created', 'claimed', 'status_change', 'priority_change', 'assigned', 'comment'
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow)

    # Relationship
    ticket = db.relationship("Ticket", backref=db.backref("activity_logs", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "ticket_id": self.ticket_id,
            "message": self.message,
            "created_by": self.created_by,
            "timestamp": self.timestamp.isoformat()
        }
