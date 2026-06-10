from flask import Blueprint, jsonify, g
from datetime import datetime
from app.models.announcement import Announcement
from app.middleware.auth_middleware import token_required

notification_bp = None # Avoid name conflicts
announcement_bp = Blueprint('announcements', __name__, url_prefix='/api/v1/announcements')

@announcement_bp.route('', methods=['GET'])
@token_required
def get_active_announcements():
    """
    Get active system-wide announcements
    ---
    tags:
      - Announcements
    security:
      - Bearer: []
    responses:
      200:
        description: List of active announcements retrieved successfully
      401:
        description: Unauthorized
    """
    from app.core.config import Config
    from app.models.user import User

    now = datetime.utcnow()
    
    # Base query
    query = Announcement.query.filter(
        Announcement.is_active == True
    ).filter(
        (Announcement.expires_at == None) | (Announcement.expires_at > now)
    )

    # Exclude demo announcements for real users
    if g.user.email != Config.DEMO_EMAIL:
        demo_user = User.query.filter_by(email=Config.DEMO_EMAIL).first()
        if demo_user:
            query = query.filter(Announcement.created_by_id != demo_user.id)

    active_announcements = query.order_by(Announcement.created_at.desc()).all()
    return jsonify([a.to_dict() for a in active_announcements]), 200
