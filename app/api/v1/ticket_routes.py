from flask import Blueprint, request, jsonify, g
from datetime import datetime
from app.services.ticket_service import TicketService
from app.schemas.ticket_schema import TicketCreate, TicketUpdate
from app.middleware.auth_middleware import token_required
from pydantic import ValidationError

from app.models.comment import Comment
from app.core.database import db

ticket_bp = Blueprint('tickets', __name__, url_prefix='/api/v1/tickets')

@ticket_bp.route('', methods=['POST'])
@token_required
def create_ticket():
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
    # TODO: Add filtering/pagination
    tickets = TicketService.get_tickets(g.user)
    # Serialize manually or use schema
    return jsonify([{
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
    } for t in tickets]), 200

@ticket_bp.route('/<int:ticket_id>', methods=['PUT', 'PATCH'])
@token_required
def update_ticket(ticket_id):
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
    try:
        from app.services.pdf_service import PDFService
        
        ticket = TicketService.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
            
        # Check permissions (creator, assignee, or admin)
        # For simplicity in this step, allowing authenticated users for now
        # Ideally: if ticket.created_by_id != g.user.id and g.user.role != 'admin' ...
        
        pdf_buffer = PDFService.generate_ticket_pdf(ticket)
        
        from flask import make_response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Ticket-{ticket.id}.pdf'
        
        return response
    except Exception as e:
        print(f"PDF Generation Error: {str(e)}") # Debug Log
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/check-duplicate', methods=['POST'])
@token_required
def check_duplicate():
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
        print(f"Duplicate Check Error: {e}")
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/<int:ticket_id>/withdraw', methods=['POST'])
@token_required
def withdraw_ticket(ticket_id):
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
        print(f"Withdraw Error: {e}")
        return jsonify({"error": str(e)}), 500

@ticket_bp.route('/<int:ticket_id>/claim', methods=['POST'])
@token_required
def claim_ticket(ticket_id):
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
