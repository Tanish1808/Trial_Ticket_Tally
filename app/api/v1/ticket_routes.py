from flask import Blueprint, request, jsonify, g
from datetime import datetime
from app.services.ticket_service import TicketService
from app.services.sla_service import SLAService
from app.schemas.ticket_schema import TicketCreate, TicketUpdate
from app.schemas.csat_feedback_schema import CSATFeedbackCreate
from app.utils.time_utils import utcnow
from app.middleware.auth_middleware import token_required
from pydantic import ValidationError
from app.core.extensions import limiter

from app.models.comment import Comment
from app.models.csat_feedback import CSATFeedback
from app.core.database import db
import logging

logger = logging.getLogger(__name__)

ticket_bp = Blueprint('tickets', __name__, url_prefix='/api/v1/tickets')

@ticket_bp.route('', methods=['POST'])
@limiter.limit("10 per minute")
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
        
    from app.models.reopen_request import ReopenRequest
    rr = ReopenRequest.query.filter_by(ticket_id=ticket.id).order_by(ReopenRequest.requested_at.desc()).first()
        
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
        "slaDeadline": SLAService.get_deadline(ticket).isoformat() + "Z",
        "slaStatus": SLAService.check_sla_status(ticket).value,
        "createdByName": ticket.creator.full_name if ticket.creator else "Unknown",
        "createdById": ticket.created_by_id,
        "github_pr_url": ticket.github_pr_url,
        "githubPrUrl": ticket.github_pr_url,
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
        "feedback": {
            "rating": ticket.feedback.rating,
            "comment": ticket.feedback.comment,
            "createdAt": ticket.feedback.created_at.isoformat()
        } if ticket.feedback else None,
        "reopen_request": {
            "id": rr.id,
            "status": rr.status,
            "reason": rr.reason,
            "decline_reason": rr.decline_reason,
            "createdAt": rr.requested_at.isoformat()
        } if rr else None,
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
    sla_map = SLAService.get_sla_map()
    
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
            "slaDeadline": SLAService.get_deadline(t, sla_map=sla_map).isoformat() + "Z",
            "slaStatus": SLAService.check_sla_status(t, sla_map=sla_map).value,
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
            "perPage": paginated_tickets.per_page,
            "total_pages": paginated_tickets.pages,
            "totalPages": paginated_tickets.pages,
            "total_items": paginated_tickets.total,
            "totalItems": paginated_tickets.total
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
        from app.core.constants import TicketStatus
        data = request.json
        if not data or 'text' not in data:
            return jsonify({"error": "Comment text required"}), 400
            
        ticket = TicketService.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404

        if ticket.status == TicketStatus.CLOSED:
            return jsonify({"error": "Cannot add comments to a closed ticket"}), 400
            
        comment = Comment(
            text=data['text'],
            ticket_id=ticket_id,
            user_id=g.user.id,
            parent_id=data.get('parent_id')
        )
        db.session.add(comment)
        
        # Update ticket updated_at
        ticket.updated_at = utcnow()
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
        
        ticket = db.session.get(Ticket, ticket_id)
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
        
        ticket.updated_at = utcnow()
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

@ticket_bp.route('/<int:ticket_id>/feedback', methods=['POST'])
@token_required
def submit_feedback(ticket_id):
    """
    Submit CSAT Feedback for a ticket (Employee creator only, resolved/closed status only)
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
            - rating
          properties:
            rating:
              type: integer
              minimum: 1
              maximum: 5
              example: 5
            comment:
              type: string
              example: Great service!
    responses:
      201:
        description: Feedback submitted successfully
      400:
        description: Invalid feedback data or invalid ticket status
      401:
        description: Unauthorized
      403:
        description: Forbidden (Not the creator of the ticket)
      404:
        description: Ticket not found
      409:
        description: Feedback already exists for this ticket
    """
    try:
        from app.models.ticket import Ticket
        from app.core.constants import TicketStatus
        from app.services.notification_service import NotificationService
        
        ticket = db.session.get(Ticket, ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
            
        # Permission check: must be the creator of the ticket
        if ticket.created_by_id != g.user.id:
            return jsonify({"error": "Only the ticket creator can submit feedback"}), 403
            
        # Status check: must be Resolved or Closed
        if ticket.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            return jsonify({"error": "Feedback can only be submitted for Resolved or Closed tickets"}), 400
            
        # Duplicate check: check if feedback already exists
        if ticket.feedback:
            return jsonify({"error": "Feedback has already been submitted for this ticket"}), 409
            
        # Validate body
        data = CSATFeedbackCreate(**request.json)
        
        feedback = CSATFeedback(
            rating=data.rating,
            comment=data.comment,
            ticket_id=ticket.id,
            user_id=g.user.id
        )
        db.session.add(feedback)
        
        # Add timeline entry (system comment or update ticket updated_at)
        ticket.updated_at = utcnow()
        db.session.commit()
        
        # Broadcast activity log event via WebSocket & save to DB
        NotificationService.broadcast_live_activity(
            category="feedback",
            ticket_id=ticket.id,
            message=f"CSAT rating of {feedback.rating}/5 stars submitted for Ticket T-{1000 + ticket.id} by {g.user.full_name}.",
            created_by=g.user.full_name
        )
        
        return jsonify({
            "message": "Feedback submitted successfully",
            "feedback": {
                "id": feedback.id,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "createdAt": feedback.created_at.isoformat()
            }
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/<int:ticket_id>/reopen-request', methods=['POST'])
@token_required
def create_reopen_request(ticket_id):
    from app.models.reopen_request import ReopenRequest
    from app.models.ticket import Ticket
    from app.core.constants import TicketStatus, UserRole
    from datetime import timedelta
    from app.services.notification_service import NotificationService
    
    try:
        ticket = db.session.get(Ticket, ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
            
        # Check permissions: only the ticket creator (employee) can request a reopen
        if g.user.role != UserRole.EMPLOYEE or ticket.created_by_id != g.user.id:
            return jsonify({"error": "Unauthorized: Only the ticket creator can request a reopen"}), 403
            
        # Check status: must be Resolved
        if ticket.status != TicketStatus.RESOLVED:
            return jsonify({"error": f"Cannot request reopen on a ticket that is {ticket.status.value}"}), 400
            
        # Check 7-day cutoff (Resolved within last 7 days)
        last_activity = ticket.updated_at if ticket.updated_at else ticket.created_at
        cutoff_date = utcnow() - timedelta(days=7)
        if last_activity < cutoff_date:
            return jsonify({"error": "Cannot request reopen: 7-day limit has passed"}), 400
            
        # Check for existing pending reopen requests
        existing_request = ReopenRequest.query.filter_by(ticket_id=ticket.id, status='pending').first()
        if existing_request:
            return jsonify({"error": "A reopen request is already pending for this ticket"}), 400
            
        # Get reason from payload
        json_data = request.get_json(silent=True) or {}
        reason = json_data.get('reason')
        if not reason or len(reason.strip()) < 15:
            return jsonify({"error": "A valid reason (minimum 15 characters) is required to request reopen"}), 400
            
        # Create reopen request
        reopen_req = ReopenRequest(
            ticket_id=ticket.id,
            requested_by_id=g.user.id,
            reason=reason.strip()
        )
        db.session.add(reopen_req)
        db.session.commit()
        
        # Notify Admins
        from app.models.user import User
        admins = User.query.filter_by(role=UserRole.ADMIN).all()
        for admin in admins:
            NotificationService.create_notification(
                user_id=admin.id,
                title="Ticket Reopen Requested",
                message=f"Reopen requested for Ticket T-{1000 + ticket.id} by {g.user.full_name}.",
                type='info'
            )
            
        # Broadcast activity
        NotificationService.broadcast_live_activity(
            category="reopen_requested",
            ticket_id=ticket.id,
            message=f"Reopen request submitted for Ticket T-{1000 + ticket.id} by {g.user.full_name}.",
            created_by=g.user.full_name
        )
        
        return jsonify({
            "message": "Reopen request submitted successfully",
            "request_id": reopen_req.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
