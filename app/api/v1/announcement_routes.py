from flask import Blueprint, jsonify
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
    now = datetime.utcnow()
    # Query announcements that are active AND (expires_at is null OR expires_at > now)
    active_announcements = Announcement.query.filter(
        Announcement.is_active == True
    ).filter(
        (Announcement.expires_at == None) | (Announcement.expires_at > now)
    ).order_by(Announcement.created_at.desc()).all()

    return jsonify([a.to_dict() for a in active_announcements]), 200
