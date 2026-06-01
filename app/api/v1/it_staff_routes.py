from flask import Blueprint, jsonify, g
from app.models.ticket import Ticket
from app.middleware.auth_middleware import role_required
from app.core.constants import UserRole, TicketStatus

it_staff_bp = Blueprint('it_staff', __name__, url_prefix='/api/v1/it-staff')

@it_staff_bp.route('/assigned-tickets', methods=['GET'])
@role_required([UserRole.IT_STAFF, UserRole.ADMIN])
def get_assigned_tickets():
    """
    Get tickets assigned to the logged-in IT staff member
    ---
    tags:
      - IT Staff
    security:
      - Bearer: []
    responses:
      200:
        description: List of assigned tickets retrieved successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (IT Staff or Admin only)
    """
    tickets = Ticket.query.filter_by(assigned_to_id=g.user.id).all()
    return jsonify([{
        "id": t.id,
        "title": t.title,
        "status": t.status.value,
        "priority": t.priority.value
    } for t in tickets])

@it_staff_bp.route('/team-tickets', methods=['GET'])
@role_required([UserRole.IT_STAFF, UserRole.ADMIN])
def get_team_tickets():
    """
    Get tickets assigned to the IT staff member's team
    ---
    tags:
      - IT Staff
    security:
      - Bearer: []
    responses:
      200:
        description: List of team tickets retrieved successfully
      400:
        description: User is not assigned to any team
      401:
        description: Unauthorized
      403:
        description: Forbidden (IT Staff or Admin only)
    """
    if not g.user.team_id:
         return jsonify({"error": "User not assigned to a team"}), 400
         
    tickets = Ticket.query.filter_by(team_id=g.user.team_id).all()
    return jsonify([{
        "id": t.id,
        "title": t.title,
        "status": t.status.value
    } for t in tickets])
