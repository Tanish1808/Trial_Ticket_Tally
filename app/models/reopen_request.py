from app.utils.time_utils import utcnow
from app.core.database import db

class ReopenRequest(db.Model):
    __tablename__ = "reopen_requests"

    id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False) # pending, approved, declined
    decline_reason = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Foreign Keys
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    
    # Relationships
    ticket = db.relationship("Ticket", backref=db.backref("reopen_requests", cascade="all, delete-orphan"))
    requested_by = db.relationship("User", foreign_keys=[requested_by_id], backref="requested_reopens")
    resolved_by = db.relationship("User", foreign_keys=[resolved_by_id], backref="resolved_reopens")

    def __repr__(self):
        return f"<ReopenRequest {self.id} for Ticket {self.ticket_id} - Status: {self.status}>"
