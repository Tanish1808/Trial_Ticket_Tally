from flask import Blueprint, request, jsonify, g
from app.models.event import Event
from app.core.database import db
from app.middleware.auth_middleware import token_required, role_required
from app.core.constants import UserRole
from app.schemas.event_schema import EventCreate, EventUpdate
from pydantic import ValidationError
from datetime import datetime

event_bp = Blueprint('events', __name__, url_prefix='/api/v1/events')

@event_bp.route('', methods=['GET'])
@token_required
def get_events():
    """
    Get all calendar events
    ---
    tags:
      - Events
    security:
      - Bearer: []
    responses:
      200:
        description: List of all calendar events retrieved successfully
      401:
        description: Unauthorized
    """
    events = Event.query.order_by(Event.start_time.asc()).all()
    return jsonify([e.to_dict() for e in events]), 200

@event_bp.route('', methods=['POST'])
@role_required([UserRole.ADMIN])
def create_event():
    """
    Create a new event (Admin only)
    ---
    tags:
      - Events
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
            - event_type
            - start_time
            - end_time
          properties:
            title:
              type: string
              example: Main DB Maintenance
            description:
              type: string
              example: Database version upgrade downtime
            event_type:
              type: string
              enum: [maintenance, training, system_update, other]
              example: maintenance
            start_time:
              type: string
              format: date-time
              example: "2026-06-15T02:00:00Z"
            end_time:
              type: string
              format: date-time
              example: "2026-06-15T04:00:00Z"
    responses:
      201:
        description: Event created successfully
      400:
        description: Validation error
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
    """
    try:
        data = EventCreate(**request.json)
        
        # Additional custom validation: end_time must be after start_time
        if data.end_time <= data.start_time:
            return jsonify({"error": "End time must be after start time"}), 400

        event = Event(
            title=data.title,
            description=data.description,
            event_type=data.event_type,
            start_time=data.start_time,
            end_time=data.end_time,
            created_by_id=g.user.id
        )
        db.session.add(event)
        db.session.commit()
        
        return jsonify({
            "message": "Event created successfully",
            "event": event.to_dict()
        }), 201
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@event_bp.route('/<int:event_id>', methods=['PATCH'])
@role_required([UserRole.ADMIN])
def update_event(event_id):
    """
    Update event details (Admin only)
    ---
    tags:
      - Events
    security:
      - Bearer: []
    parameters:
      - name: event_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        required: true
    responses:
      200:
        description: Event updated successfully
      400:
        description: Validation or scheduling error
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
      404:
        description: Event not found
    """
    event = Event.query.get_or_404(event_id)
    try:
        data = EventUpdate(**request.json)
        
        if data.title is not None:
            event.title = data.title
        if data.description is not None:
            event.description = data.description
        if data.event_type is not None:
            event.event_type = data.event_type
            
        new_start = data.start_time if data.start_time is not None else event.start_time
        new_end = data.end_time if data.end_time is not None else event.end_time
        
        if new_end <= new_start:
            return jsonify({"error": "End time must be after start time"}), 400
            
        if data.start_time is not None:
            event.start_time = data.start_time
        if data.end_time is not None:
            event.end_time = data.end_time
            
        db.session.commit()
        return jsonify({
            "message": "Event updated successfully",
            "event": event.to_dict()
        }), 200
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@event_bp.route('/<int:event_id>', methods=['DELETE'])
@role_required([UserRole.ADMIN])
def delete_event(event_id):
    """
    Delete an event (Admin only)
    ---
    tags:
      - Events
    security:
      - Bearer: []
    parameters:
      - name: event_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Event deleted successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
      404:
        description: Event not found
    """
    event = Event.query.get_or_404(event_id)
    try:
        db.session.delete(event)
        db.session.commit()
        return jsonify({"message": "Event deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
