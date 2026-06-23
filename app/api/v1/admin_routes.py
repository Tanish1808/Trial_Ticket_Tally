from flask import Blueprint, jsonify
from app.middleware.auth_middleware import role_required
from app.core.constants import UserRole
from app.models.ticket import Ticket
from app.models.user import User

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')

@admin_bp.route('/analytics', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_analytics():
    """
    Get system-wide analytics and ticket metrics (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    responses:
      200:
        description: System analytics data retrieved successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
    """
    # Simple dashboard stats
    total_tickets = Ticket.query.count()
    open_tickets = Ticket.query.filter(Ticket.status == 'Open').count()
    users_count = User.query.count()
    
    return jsonify({
        "total_tickets": total_tickets,
        "totalTickets": total_tickets,
        "open_tickets": open_tickets,
        "openTickets": open_tickets,
        "total_users": users_count,
        "totalUsers": users_count
    })

@admin_bp.route('/messages', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_messages():
    """
    Get contact form messages list (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    responses:
      200:
        description: List of contact form messages retrieved successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
    """
    from app.models.message import Message
    messages = Message.query.order_by(Message.created_at.desc()).all()
    
    return jsonify([{
        'id': msg.id,
        'name': msg.name,
        'email': msg.email,
        'subject': msg.subject,
        'message': msg.message,
        'created_at': msg.created_at.isoformat(),
        'createdAt': msg.created_at.isoformat(),
        'is_read': msg.is_read,
        'isRead': msg.is_read
    } for msg in messages])

@admin_bp.route('/messages/<int:message_id>/read', methods=['PATCH'])
@role_required([UserRole.ADMIN])
def mark_message_read(message_id):
    """
    Mark a contact form message as read (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - name: message_id
        in: path
        type: integer
        required: true
        description: The ID of the message to mark as read
    responses:
      200:
        description: Message marked as read successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
      404:
        description: Message not found
    """
    from app.models.message import Message
    from app.core.database import db
    
    message = db.get_or_404(Message, message_id)
    message.is_read = True
    db.session.commit()
    
    return jsonify({'message': 'Message marked as read'})


@admin_bp.route('/team-mappings', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_team_mappings():
    """
    Get list of all category-to-team routing mappings (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    responses:
      200:
        description: List of team routing mappings retrieved successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
    """
    from app.models.team_mapping import TeamMapping
    mappings = TeamMapping.query.all()
    return jsonify([{
        'id': m.id,
        'category': m.category,
        'team_id': m.team_id,
        'teamId': m.team_id,
        'team_name': m.team.name if m.team else None,
        'teamName': m.team.name if m.team else None
    } for m in mappings])


@admin_bp.route('/team-mappings', methods=['POST'])
@role_required([UserRole.ADMIN])
def create_team_mapping():
    """
    Create a new category-to-team routing mapping (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - category
            - team_id
          properties:
            category:
              type: string
              example: Custom Software issue
            team_id:
              type: integer
              example: 1
    responses:
      201:
        description: Team mapping created successfully
      400:
        description: Duplicate category mapping or target team not found
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
    """
    from app.models.team_mapping import TeamMapping
    from app.models.team import Team
    from app.schemas.team_mapping_schema import TeamMappingCreate
    from app.core.database import db
    from flask import request
    from pydantic import ValidationError
    
    try:
        data = TeamMappingCreate(**request.json)
        
        # Verify team exists
        team = db.session.get(Team, data.team_id)
        if not team:
            return jsonify({'error': 'Target team not found'}), 400
            
        # Check duplicate category
        existing = TeamMapping.query.filter_by(category=data.category).first()
        if existing:
            return jsonify({'error': f'Mapping for category "{data.category}" already exists'}), 400
            
        mapping = TeamMapping(category=data.category, team_id=data.team_id)
        db.session.add(mapping)
        db.session.commit()
        
        return jsonify({
            'message': 'Team mapping created',
            'id': mapping.id,
            'category': mapping.category,
            'team_id': mapping.team_id,
            'teamId': mapping.team_id,
            'team_name': mapping.team.name if mapping.team else None,
            'teamName': mapping.team.name if mapping.team else None
        }), 201
    except ValidationError as e:
        return jsonify({'error': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/team-mappings/<int:mapping_id>', methods=['PUT', 'PATCH'])
@role_required([UserRole.ADMIN])
def update_team_mapping(mapping_id):
    """
    Update category-to-team routing mapping (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - name: mapping_id
        in: path
        type: integer
        required: true
        description: The ID of the mapping to update
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            category:
              type: string
              example: Updated custom category
            team_id:
              type: integer
              example: 2
    responses:
      200:
        description: Team mapping updated successfully
      400:
        description: Validation or duplicate category error
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
      404:
        description: Mapping not found
    """
    from app.models.team_mapping import TeamMapping
    from app.models.team import Team
    from app.schemas.team_mapping_schema import TeamMappingUpdate
    from app.core.database import db
    from flask import request
    from pydantic import ValidationError
    
    try:
        mapping = db.get_or_404(TeamMapping, mapping_id)
        data = TeamMappingUpdate(**request.json)
        
        if data.category is not None:
            if data.category != mapping.category:
                existing = TeamMapping.query.filter_by(category=data.category).first()
                if existing:
                    return jsonify({'error': f'Mapping for category "{data.category}" already exists'}), 400
            mapping.category = data.category
            
        if data.team_id is not None:
            team = db.session.get(Team, data.team_id)
            if not team:
                return jsonify({'error': 'Target team not found'}), 400
            mapping.team_id = data.team_id
            
        db.session.commit()
        return jsonify({
            'message': 'Team mapping updated',
            'id': mapping.id,
            'category': mapping.category,
            'team_id': mapping.team_id,
            'teamId': mapping.team_id,
            'team_name': mapping.team.name if mapping.team else None,
            'teamName': mapping.team.name if mapping.team else None
        })
    except ValidationError as e:
        return jsonify({'error': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/team-mappings/<int:mapping_id>', methods=['DELETE'])
@role_required([UserRole.ADMIN])
def delete_team_mapping(mapping_id):
    """
    Delete a category-to-team routing mapping (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - name: mapping_id
        in: path
        type: integer
        required: true
        description: The ID of the mapping to delete
    responses:
      200:
        description: Team mapping deleted successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
      404:
        description: Mapping not found
    """
    from app.models.team_mapping import TeamMapping
    from app.core.database import db
    
    try:
        mapping = db.get_or_404(TeamMapping, mapping_id)
        db.session.delete(mapping)
        db.session.commit()
        return jsonify({'message': 'Team mapping deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/purge', methods=['POST'])
@role_required([UserRole.ADMIN])
def trigger_purge():
    """
    Manually trigger data retention archiving and purging (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    responses:
      200:
        description: Purge operation completed successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
      500:
        description: Internal server error
    """
    from app.services.ticket_service import TicketService
    try:
        count = TicketService.archive_and_purge_old_tickets()
        return jsonify({
            "status": "success",
            "message": f"Successfully archived and purged {count} tickets.",
            "count": count
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@admin_bp.route('/announcements', methods=['POST'])
@role_required([UserRole.ADMIN])
def create_announcement():
    """
    Create a new system announcement (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - message
          properties:
            title:
              type: string
              example: Maintenance window scheduled
            message:
              type: string
              example: The system will be down on Sunday at 2 AM.
            expires_at:
              type: string
              format: date-time
              example: 2026-06-12T02:00:00Z
    responses:
      201:
        description: Announcement created successfully
      400:
        description: Validation error
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
    """
    from app.models.announcement import Announcement
    from app.schemas.announcement_schema import AnnouncementCreate
    from app.core.database import db
    from flask import request, g
    from pydantic import ValidationError

    try:
        data = AnnouncementCreate(**request.json)
        announcement = Announcement(
            title=data.title,
            message=data.message,
            expires_at=data.expires_at,
            created_by_id=g.user.id
        )
        db.session.add(announcement)
        db.session.commit()

        return jsonify({
            'message': 'Announcement created',
            'announcement': announcement.to_dict()
        }), 201
    except ValidationError as e:
        return jsonify({'error': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/announcements', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_all_announcements():
    """
    Get all system announcements (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    responses:
      200:
        description: List of all announcements
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
    """
    from app.models.announcement import Announcement
    from app.core.config import Config
    from app.models.user import User

    query = Announcement.query
    
    # Exclude demo announcements for real administrators
    if g.user.email != Config.DEMO_EMAIL:
        demo_user = User.query.filter_by(email=Config.DEMO_EMAIL).first()
        if demo_user:
            query = query.filter(Announcement.created_by_id != demo_user.id)

    announcements = query.order_by(Announcement.created_at.desc()).all()
    return jsonify([a.to_dict() for a in announcements]), 200

@admin_bp.route('/announcements/<int:announcement_id>', methods=['DELETE'])
@role_required([UserRole.ADMIN])
def delete_announcement(announcement_id):
    """
    Delete system announcement (Admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - name: announcement_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Announcement deleted successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
      404:
        description: Announcement not found
    """
    from app.models.announcement import Announcement
    from app.core.database import db

    announcement = db.get_or_404(Announcement, announcement_id)
    try:
        db.session.delete(announcement)
        db.session.commit()
        return jsonify({'message': 'Announcement deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


