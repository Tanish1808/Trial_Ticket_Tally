from flask import Blueprint, jsonify
from app.middleware.auth_middleware import role_required
from app.core.constants import UserRole
from app.models.ticket import Ticket
from app.models.user import User

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')

@admin_bp.route('/analytics', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_analytics():
    # Simple dashboard stats
    total_tickets = Ticket.query.count()
    open_tickets = Ticket.query.filter(Ticket.status == 'Open').count()
    users_count = User.query.count()
    
    return jsonify({
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "total_users": users_count
    })

@admin_bp.route('/messages', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_messages():
    from app.models.message import Message
    messages = Message.query.order_by(Message.created_at.desc()).all()
    
    return jsonify([{
        'id': msg.id,
        'name': msg.name,
        'email': msg.email,
        'subject': msg.subject,
        'message': msg.message,
        'created_at': msg.created_at.isoformat(),
        'is_read': msg.is_read
    } for msg in messages])

@admin_bp.route('/messages/<int:message_id>/read', methods=['PATCH'])
@role_required([UserRole.ADMIN])
def mark_message_read(message_id):
    from app.models.message import Message
    from app.core.database import db
    
    message = Message.query.get_or_404(message_id)
    message.is_read = True
    db.session.commit()
    
    return jsonify({'message': 'Message marked as read'})
