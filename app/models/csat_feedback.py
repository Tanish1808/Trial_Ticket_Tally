from app.utils.time_utils import utcnow
from app.core.database import db

class CSATFeedback(db.Model):
    __tablename__ = "csat_feedbacks"

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    # Foreign Keys
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    # Relationships
    ticket = db.relationship("Ticket", back_populates="feedback")
    user = db.relationship("User", backref="feedbacks")

    def __repr__(self):
        return f"<CSATFeedback {self.id} (Rating: {self.rating}) for Ticket {self.ticket_id}>"
