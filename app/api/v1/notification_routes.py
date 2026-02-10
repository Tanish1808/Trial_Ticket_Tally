from flask import Blueprint, request, jsonify, g
from app.services.notification_service import NotificationService
from app.middleware.auth_middleware import token_required

notification_bp = Blueprint('notification_bp', __name__)

@notification_bp.route('/', methods=['GET'])
@token_required
def get_notifications():
    user = g.user
    notifications = NotificationService.get_notifications(user.id)
    unread_count = NotificationService.get_unread_count(user.id)
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': unread_count
    })

@notification_bp.route('/<int:notification_id>/read', methods=['POST'])
@token_required
def mark_read(notification_id):
    user = g.user
    success = NotificationService.mark_as_read(notification_id, user.id)
    if success:
        return jsonify({'message': 'Notification marked as read'})
    return jsonify({'error': 'Notification not found'}), 404

@notification_bp.route('/read-all', methods=['POST'])
@token_required
def mark_all_read():
    user = g.user
    NotificationService.mark_all_as_read(user.id)
    return jsonify({'message': 'All notifications marked as read'})

@notification_bp.route('/', methods=['DELETE'])
@token_required
def clear_notifications():
    user = g.user
    NotificationService.clear_all_notifications(user.id)
    return jsonify({'message': 'Notifications cleared'})
