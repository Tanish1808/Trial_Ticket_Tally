from flask import Blueprint, request, jsonify, g
from datetime import datetime
from app.services.ticket_service import TicketService
from app.schemas.ticket_schema import TicketCreate, TicketUpdate
from app.middleware.auth_middleware import token_required
from pydantic import ValidationError

from app.models.comment import Comment
from app.core.database import db
import logging

logger = logging.getLogger(__name__)

ticket_bp = Blueprint('tickets', __name__, url_prefix='/api/v1/tickets')

@ticket_bp.route('', methods=['POST'])
@token_required
def create_ticket():
    """
    Create a new IT support ticket
    ---
    tags:
      - Tickets
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
            - description
            - category
          properties:
            title:
              type: string
              example: VPN Connection Failure
            description:
              type: string
              example: Cannot connect to home VPN, getting timeout error.
            category:
              type: string
              example: Network Issue
            priority:
              type: string
              enum: [LOW, MEDIUM, HIGH, CRITICAL]
              default: MEDIUM
              example: HIGH
            team_id:
              type: integer
              example: 1
    responses:
      201:
        description: Ticket created successfully
        schema:
          type: object
          properties:
            message:
              type: string
            ticket_id:
              type: integer
      400:
        description: Validation error
      401:
        description: Unauthorized
    """
    try:
        data = TicketCreate(**request.json)
        ticket = TicketService.create_ticket(data, g.user.id)
        return jsonify({"message": "Ticket created", "ticket_id": ticket.id}), 201
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/<int:ticket_id>', methods=['GET'])
@token_required
def get_ticket(ticket_id):
    """
    Get ticket details by ID (including comments and history)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - name: ticket_id
        in: path
        type: integer
        required: true
        description: The ID of the ticket to retrieve
    responses:
      200:
        description: Ticket details retrieved successfully
      401:
        description: Unauthorized
      404:
        description: Ticket not found
    """
    ticket = TicketService.get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
        
    return jsonify({
        "id": ticket.id, 
        "title": ticket.title, 
        "subject": ticket.title, # Alias for frontend compatibility
        "description": ticket.description,
        "category": ticket.category,
        "status": ticket.status.value, 
        "priority": ticket.priority.value,
        "createdAt": ticket.created_at.isoformat(),
        "updatedAt": ticket.updated_at.isoformat() if ticket.updated_at else ticket.created_at.isoformat(),
        "createdByName": ticket.creator.full_name if ticket.creator else "Unknown",
        "createdById": ticket.created_by_id,
        "assignedTo": (
            f"{ticket.team.name} : {ticket.assignee.full_name}" 
            if ticket.assignee and ticket.team 
            else (ticket.assignee.full_name if ticket.assignee else (ticket.team.name if ticket.team else None))
        ),
        "comments": [{
            "id": c.id,
            "text": c.text,
            "author": c.author.full_name,
            "timestamp": c.created_at.isoformat(),
            "parentId": c.parent_id
        } for c in ticket.comments],
        "timeline": [{
            "action": f"Status changed from {h.old_status.value if h.old_status else 'None'} to {h.new_status.value}",
            "by": h.changed_by.full_name if h.changed_by else "System",
            "timestamp": h.changed_at.isoformat()
        } for h in ticket.status_history] + [{
            "action": "Comment added",
            "by": c.author.full_name,
            "timestamp": c.created_at.isoformat(),
            "note": c.text[:50] + "..." if len(c.text) > 50 else c.text
        } for c in ticket.comments]
    }), 200

@ticket_bp.route('', methods=['GET'])
@token_required
def get_tickets():
    """
    List tickets with pagination (filtered by user role)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        default: 20
        maximum: 100
        description: Items per page (capped at 100)
    responses:
      200:
        description: List of tickets and pagination metadata
      401:
        description: Unauthorized
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    if per_page > 100:
        per_page = 100
    
    paginated_tickets = TicketService.get_tickets(g.user, page=page, per_page=per_page)
    
    return jsonify({
        "items": [{
            "id": t.id, 
            "title": t.title, 
            "description": t.description,
            "category": t.category,
            "status": t.status.value, 
            "priority": t.priority.value,
            "createdAt": t.created_at.isoformat(),
            "updatedAt": t.updated_at.isoformat() if t.updated_at else t.created_at.isoformat(),
            "createdByName": t.creator.full_name if t.creator else "Unknown",
            "createdById": t.created_by_id,
            "assignedToId": t.assigned_to_id,
            "assignedTo": (
                f"{t.team.name} : {t.assignee.full_name}" 
                if t.assignee and t.team 
                else (t.assignee.full_name if t.assignee else (t.team.name if t.team else None))
            )
        } for t in paginated_tickets.items],
        "meta": {
            "page": paginated_tickets.page,
            "per_page": paginated_tickets.per_page,
            "total_pages": paginated_tickets.pages,
            "total_items": paginated_tickets.total
        }
    }), 200

@ticket_bp.route('/<int:ticket_id>', methods=['PUT', 'PATCH'])
@token_required
def update_ticket(ticket_id):
    """
    Update an existing ticket (status, priority, category, assignee, team)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - name: ticket_id
        in: path
        type: integer
        required: true
        description: The ID of the ticket to update
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [OPEN, IN_PROGRESS, RESOLVED, CLOSED, WITHDRAWN]
              example: RESOLVED
            priority:
              type: string
              enum: [LOW, MEDIUM, HIGH, CRITICAL]
              example: HIGH
            category:
              type: string
              example: Software Issue
            assigned_to_id:
              type: integer
              example: 2
            team_id:
              type: integer
              example: 1
    responses:
      200:
        description: Ticket updated successfully
      401:
        description: Unauthorized
      404:
        description: Ticket not found or value error
    """
    try:
        data = TicketUpdate(**request.json)
        TicketService.update_ticket(ticket_id, data, g.user.id)
        return jsonify({"message": "Ticket updated"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/<int:ticket_id>/comments', methods=['POST'])
@token_required
def add_comment(ticket_id):
    """
    Add a comment to a ticket
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - name: ticket_id
        in: path
        type: integer
        required: true
        description: The ID of the ticket
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - text
          properties:
            text:
              type: string
              example: Working on a fix now.
            parent_id:
              type: integer
              description: Optional ID of the parent comment for nesting
    responses:
      201:
        description: Comment added successfully
      400:
        description: Missing comment text
      401:
        description: Unauthorized
      404:
        description: Ticket not found
    """
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({"error": "Comment text required"}), 400
            
        ticket = TicketService.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
            
        comment = Comment(
            text=data['text'],
            ticket_id=ticket_id,
            user_id=g.user.id,
            parent_id=data.get('parent_id')
        )
        db.session.add(comment)
        
        # Update ticket updated_at
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Notify
        from app.services.notification_service import NotificationService
        NotificationService.notify_new_comment(ticket, comment, g.user)
        
        return jsonify({
            "message": "Comment added",
            "comment": {
                "id": comment.id,
                "text": comment.text,
                "author": g.user.full_name,
                "timestamp": comment.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/<int:ticket_id>/pdf', methods=['GET'])
@token_required
def download_pdf(ticket_id):
    """
    Download ticket report as PDF (restricted access)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - name: ticket_id
        in: path
        type: integer
        required: true
        description: The ID of the ticket
    responses:
      200:
        description: PDF binary file
      401:
        description: Unauthorized
      403:
        description: Forbidden (no permissions to access this ticket's PDF)
      404:
        description: Ticket not found
    """
    try:
        from app.services.pdf_service import PDFService
        
        ticket = TicketService.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
            
        # Check permissions (creator, assignee, team members, or admin)
        from app.core.constants import UserRole
        if (g.user.role != UserRole.ADMIN and 
            ticket.created_by_id != g.user.id and 
            ticket.assigned_to_id != g.user.id and 
            (ticket.team_id is None or g.user.team_id != ticket.team_id)):
            return jsonify({"error": "Unauthorized"}), 403
        
        pdf_buffer = PDFService.generate_ticket_pdf(ticket)
        
        from flask import make_response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Ticket-{ticket.id}.pdf'
        
        return response
    except Exception as e:
        logger.error(f"PDF Generation Error: {str(e)}") # Debug Log
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/check-duplicate', methods=['POST'])
@token_required
def check_duplicate():
    """
    Check for existing similar active tickets by the current user
    ---
    tags:
      - Tickets
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
          properties:
            title:
              type: string
              example: VPN down again
    responses:
      200:
        description: Duplicate check result
      400:
        description: Title required
      401:
        description: Unauthorized
    """
    try:
        data = request.json
        if not data or 'title' not in data:
            return jsonify({"error": "Title required"}), 400
            
        title = data['title'].strip()
        if not title:
             return jsonify({"exists": False}), 200

        # Search for similar active tickets by this user
        # Uses ILIKE for case-insensitive matching if DB supports it (Postgres), otherwise standard query
        # For SQLite (Project DB likely), strict equality or lower() might be needed if ilike isn't setup. 
        # But simple ilike often works in SQLAlchemy for SQLite too.
        from app.models.ticket import Ticket
        from app.core.constants import TicketStatus
        from sqlalchemy import or_

        existing_ticket = Ticket.query.filter(
            Ticket.created_by_id == g.user.id,
            Ticket.title.ilike(f"%{title}%"), # Fuzzy match contains
            Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
        ).first()

        if existing_ticket:
            return jsonify({
                "exists": True,
                "ticket": {
                    "id": existing_ticket.id,
                    "title": existing_ticket.title,
                    "status": existing_ticket.status.value,
                    "createdAt": existing_ticket.created_at.isoformat()
                }
            }), 200
        
        return jsonify({"exists": False}), 200

    except Exception as e:
        logger.error(f"Duplicate Check Error: {e}")
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/<int:ticket_id>/withdraw', methods=['POST'])
@token_required
def withdraw_ticket(ticket_id):
    """
    Withdraw a ticket (Creator only, must be in OPEN status)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - name: ticket_id
        in: path
        type: integer
        required: true
        description: The ID of the ticket to withdraw
    responses:
      200:
        description: Ticket withdrawn successfully
      400:
        description: Ticket not open or withdrawal validation failed
      401:
        description: Unauthorized
      403:
        description: Forbidden (not the creator of the ticket)
      404:
        description: Ticket not found
    """
    try:
        from app.models.ticket import Ticket
        from app.core.constants import TicketStatus
        
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
            
        # Permission Check: Must be creator
        if ticket.created_by_id != g.user.id:
            return jsonify({"error": "Unauthorized"}), 403
            
        # Status Check: Must be OPEN
        if ticket.status != TicketStatus.OPEN:
            return jsonify({"error": "Only Open tickets can be withdrawn"}), 400
            
        # Action: Withdraw Ticket
        ticket.status = TicketStatus.WITHDRAWN
        
        # Add System Comment
        comment = Comment(
            text="Ticket withdrawn by user.",
            ticket_id=ticket.id,
            user_id=g.user.id # Or admin/system ID if preferred, but user action so user ID is fine
        )
        db.session.add(comment)
        
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({"message": "Ticket withdrawn successfully"}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Withdraw Error: {e}")
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/<int:ticket_id>/claim', methods=['POST'])
@token_required
def claim_ticket(ticket_id):
    """
    Claim a ticket (IT staff only)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - name: ticket_id
        in: path
        type: integer
        required: true
        description: The ID of the ticket to claim
    responses:
      200:
        description: Ticket claimed successfully
      400:
        description: Bad request (workload limit reached, etc.)
      401:
        description: Unauthorized
      404:
        description: Ticket not found
      409:
        description: Ticket already claimed or in progress
    """
    try:
        TicketService.claim_ticket(ticket_id, g.user.id)
        return jsonify({"message": "Ticket claimed successfully"}), 200
    except ValueError as e:
        # Check specific error messages to return correct status codes
        msg = str(e)
        if "Ticket not found" in msg:
            return jsonify({"error": msg}), 404
        if "already in progress" in msg:
            return jsonify({"error": msg}), 409  # Conflict
        if "Workload limit" in msg:
            return jsonify({"error": msg}), 400  # Bad Request
            
        return jsonify({"error": msg}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
