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


@admin_bp.route('/team-mappings', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_team_mappings():
    from app.models.team_mapping import TeamMapping
    mappings = TeamMapping.query.all()
    return jsonify([{
        'id': m.id,
        'category': m.category,
        'team_id': m.team_id,
        'team_name': m.team.name if m.team else None
    } for m in mappings])


@admin_bp.route('/team-mappings', methods=['POST'])
@role_required([UserRole.ADMIN])
def create_team_mapping():
    from app.models.team_mapping import TeamMapping
    from app.models.team import Team
    from app.schemas.team_mapping_schema import TeamMappingCreate
    from app.core.database import db
    from flask import request
    from pydantic import ValidationError
    
    try:
        data = TeamMappingCreate(**request.json)
        
        # Verify team exists
        team = Team.query.get(data.team_id)
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
            'team_name': mapping.team.name if mapping.team else None
        }), 201
    except ValidationError as e:
        return jsonify({'error': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/team-mappings/<int:mapping_id>', methods=['PUT', 'PATCH'])
@role_required([UserRole.ADMIN])
def update_team_mapping(mapping_id):
    from app.models.team_mapping import TeamMapping
    from app.models.team import Team
    from app.schemas.team_mapping_schema import TeamMappingUpdate
    from app.core.database import db
    from flask import request
    from pydantic import ValidationError
    
    try:
        mapping = TeamMapping.query.get_or_404(mapping_id)
        data = TeamMappingUpdate(**request.json)
        
        if data.category is not None:
            if data.category != mapping.category:
                existing = TeamMapping.query.filter_by(category=data.category).first()
                if existing:
                    return jsonify({'error': f'Mapping for category "{data.category}" already exists'}), 400
            mapping.category = data.category
            
        if data.team_id is not None:
            team = Team.query.get(data.team_id)
            if not team:
                return jsonify({'error': 'Target team not found'}), 400
            mapping.team_id = data.team_id
            
        db.session.commit()
        return jsonify({
            'message': 'Team mapping updated',
            'id': mapping.id,
            'category': mapping.category,
            'team_id': mapping.team_id,
            'team_name': mapping.team.name if mapping.team else None
        })
    except ValidationError as e:
        return jsonify({'error': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/team-mappings/<int:mapping_id>', methods=['DELETE'])
@role_required([UserRole.ADMIN])
def delete_team_mapping(mapping_id):
    from app.models.team_mapping import TeamMapping
    from app.core.database import db
    
    try:
        mapping = TeamMapping.query.get_or_404(mapping_id)
        db.session.delete(mapping)
        db.session.commit()
        return jsonify({'message': 'Team mapping deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

