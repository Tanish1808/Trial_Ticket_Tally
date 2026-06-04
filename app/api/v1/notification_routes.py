from flask import Blueprint, request, jsonify, g
from app.services.notification_service import NotificationService
from app.middleware.auth_middleware import token_required

notification_bp = Blueprint('notification_bp', __name__)

@notification_bp.route('/', methods=['GET'])
@token_required
def get_notifications():
    """
    Get user notifications (unread and read)
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    responses:
      200:
        description: List of notifications and unread count retrieved successfully
      401:
        description: Unauthorized
    """
    user = g.user
    notifications = NotificationService.get_notifications(user.id)
    unread_count = NotificationService.get_unread_count(user.id)
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': unread_count,
        'unreadCount': unread_count
    })

@notification_bp.route('/<int:notification_id>/read', methods=['POST'])
@token_required
def mark_read(notification_id):
    """
    Mark a specific notification as read
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    parameters:
      - name: notification_id
        in: path
        type: integer
        required: true
        description: The ID of the notification to mark as read
    responses:
      200:
        description: Notification marked as read successfully
      401:
        description: Unauthorized
      404:
        description: Notification not found
    """
    user = g.user
    success = NotificationService.mark_as_read(notification_id, user.id)
    if success:
        return jsonify({'message': 'Notification marked as read'})
    return jsonify({'error': 'Notification not found'}), 404

@notification_bp.route('/read-all', methods=['POST'])
@token_required
def mark_all_read():
    """
    Mark all user notifications as read
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    responses:
      200:
        description: All notifications marked as read successfully
      401:
        description: Unauthorized
    """
    user = g.user
    NotificationService.mark_all_as_read(user.id)
    return jsonify({'message': 'All notifications marked as read'})

@notification_bp.route('/', methods=['DELETE'])
@token_required
def clear_notifications():
    """
    Clear all user notifications
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    responses:
      200:
        description: Notifications cleared successfully
      401:
        description: Unauthorized
    """
    user = g.user
    NotificationService.clear_all_notifications(user.id)
    return jsonify({'message': 'Notifications cleared'})
