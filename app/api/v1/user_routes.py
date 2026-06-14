from flask import Blueprint, jsonify, g, request
from datetime import datetime
from app.models.user import User
from app.core.database import db
from werkzeug.security import generate_password_hash
from app.middleware.auth_middleware import token_required, role_required
from app.core.constants import UserRole, TicketStatus
from app.models.ticket import Ticket

user_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')

@user_bp.route('/me', methods=['GET'])
@token_required
def get_me():
    """
    Get current logged-in user profile
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: User profile retrieved successfully
      401:
        description: Unauthorized
    """
    response_data = {
        "id": g.user.id,
        "full_name": g.user.full_name,
        "fullName": g.user.full_name,
        "email": g.user.email,
        "role": g.user.role.value,
        "department": g.user.department,
        "team_id": g.user.team_id,
        "teamId": g.user.team_id,
        "preferences": g.user.preferences or {},
        "created_at": g.user.created_at.isoformat() if g.user.created_at else None,
        "createdAt": g.user.created_at.isoformat() if g.user.created_at else None
    }
    if g.user.role in [UserRole.IT_STAFF, UserRole.ADMIN]:
        response_data["specializations"] = g.user.specializations or []

    return jsonify(response_data)

@user_bp.route('/me', methods=['PATCH'])
@token_required
def update_my_profile():
    """
    Update current user profile (full name, department, preferences)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            full_name:
              type: string
              example: John Doe
            department:
              type: string
              example: Operations
            preferences:
              type: object
              example: {"theme": "dark"}
    responses:
      200:
        description: Profile updated successfully
      401:
        description: Unauthorized
    """
    data = request.get_json()
    
    # Only allow updating specific fields
    if 'full_name' in data:
        g.user.full_name = data['full_name']
        
    if 'department' in data and g.user.role == UserRole.EMPLOYEE:
        g.user.department = data['department']

    if 'specializations' in data:
        if g.user.role in [UserRole.IT_STAFF, UserRole.ADMIN]:
            if isinstance(data['specializations'], list):
                g.user.specializations = [str(s).strip() for s in data['specializations'] if str(s).strip()]

    if 'preferences' in data:
        # Ensure it's a dict
        if isinstance(data['preferences'], dict):
            # We must assign a NEW dictionary to trigger SQLAlchemy detection for JSON types
            current_prefs = dict(g.user.preferences) if g.user.preferences else {}
            current_prefs.update(data['preferences'])
            g.user.preferences = current_prefs

    db.session.commit()
    
    user_data = {
        "id": g.user.id,
        "full_name": g.user.full_name,
        "fullName": g.user.full_name,
        "email": g.user.email,
        "role": g.user.role.value,
        "department": g.user.department
    }
    if g.user.role in [UserRole.IT_STAFF, UserRole.ADMIN]:
        user_data["specializations"] = g.user.specializations or []

    return jsonify({
        "message": "Profile updated successfully",
        "user": user_data
    })

@user_bp.route('/me/password', methods=['POST'])
@token_required
def change_my_password():
    """
    Change current user password
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - current_password
            - new_password
          properties:
            current_password:
              type: string
              example: oldsecurepassword
            new_password:
              type: string
              minLength: 6
              example: newsecurepassword
    responses:
      200:
        description: Password changed successfully
      400:
        description: Missing parameters or password too short
      401:
        description: Incorrect current password or unauthorized
    """
    data = request.get_json()
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({"error": "Current and new password are required"}), 400
        
    from werkzeug.security import check_password_hash
    
    if not check_password_hash(g.user.password_hash, current_password):
        return jsonify({"error": "Incorrect current password"}), 401
        
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters long"}), 400
        
    g.user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({"message": "Password changed successfully"})

@user_bp.route('', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_all_users():
    """
    Get list of all users (Admin only)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - name: role
        in: query
        type: string
        description: Filter users by role name
      - name: exclude_role
        in: query
        type: string
        description: Exclude users of specific role
      - name: search
        in: query
        type: string
        description: Search query matching name or email
    responses:
      200:
        description: List of users retrieved successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
    """
    role_filter = request.args.get('role')
    exclude_role = request.args.get('exclude_role')
    search_query = request.args.get('search')
    
    query = User.query
    
    # Exclude Demo User
    from app.core.config import Config
    query = query.filter(User.email != Config.DEMO_EMAIL)
    
    if search_query:
        search = f"%{search_query}%"
        # Search by name OR email
        query = query.filter((User.full_name.ilike(search)) | (User.email.ilike(search)))

    if role_filter:
        try:
            role_enum = next((r for r in UserRole if r.value == role_filter), None)
            if role_enum:
                query = query.filter(User.role == role_enum)
        except Exception:
            pass

    if exclude_role:
        try:
            exclude_enum = next((r for r in UserRole if r.value == exclude_role), None)
            if exclude_enum:
                query = query.filter(User.role != exclude_enum)
        except Exception:
            pass
            
    users = query.all()
    
    return jsonify([{
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "fullName": u.full_name,
        "role": u.role.value,
        "department": u.department,
        "team": u.team.name if u.team else None,
        "tickets_raised": len(u.created_tickets),
        "ticketsRaised": len(u.created_tickets),
        "tickets_resolved": sum(1 for t in u.assigned_tickets if t.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]),
        "ticketsResolved": sum(1 for t in u.assigned_tickets if t.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]),
        "is_active": u.is_active,
        "isActive": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "createdAt": u.created_at.isoformat() if u.created_at else None
    } for u in users])

@user_bp.route('', methods=['POST'])
@role_required([UserRole.ADMIN])
def create_user():
    """
    Create a new user account (Admin only)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - full_name
          properties:
            email:
              type: string
              format: email
              example: newuser@tt.com
            password:
              type: string
              default: password123
              example: custompass123
            full_name:
              type: string
              example: Jane Smith
            role:
              type: string
              enum: [employee, it_staff, admin]
              default: employee
              example: it_staff
            team:
              type: string
              example: IT Support
    responses:
      201:
        description: User created successfully
      400:
        description: Missing fields, duplicate email, or invalid role
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
    """
    data = request.get_json()
    
    email = data.get('email', '').lower().strip()
    password = data.get('password', 'password123') # Default password
    full_name = data.get('full_name')
    role_str = data.get('role', 'employee')
    team_name = data.get('team')
    specializations = data.get('specializations', [])
    
    if not email or not full_name:
        return jsonify({"error": "Email and Full Name are required"}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User with this email already exists"}), 400
        
    try:
        role = UserRole(role_str)
    except ValueError:
        return jsonify({"error": "Invalid role"}), 400
        
    # Handle Team assignment for IT Staff
    team_id = None
    if role == UserRole.IT_STAFF and team_name:
        from app.models.team import Team
        team = Team.query.filter_by(name=team_name).first()
        if team:
            team_id = team.id
            
    new_user = User(
        email=email,
        full_name=full_name,
        role=role,
        password_hash=generate_password_hash(password),
        team_id=team_id,
        is_active=True,
        specializations=specializations if isinstance(specializations, list) else []
    )
    
    db.session.add(new_user)
    db.session.commit()

    # Send welcome email for IT Staff / Employees created by Admin
    try:
        from app.services.email_service import EmailService
        from app.services.email_templates import get_staff_welcome_email
        
        email_body = get_staff_welcome_email(
            name=new_user.full_name,
            email=new_user.email,
            password=password,
            team_name=team_name or "General"
        )
        
        EmailService.send_email(
            new_user.email,
            "Welcome to the Team - Login Credentials 🔐",
            email_body
        )
    except Exception as e:
        # Don't fail the request if email fails, but log it
        print(f"Failed to send welcome email: {e}")

    # Notify Admin (The one who created the user)
    # We assume g.user is the admin who made the request
    from app.services.notification_service import NotificationService
    NotificationService.create_notification(
        user_id=g.user.id,
        title="User Created Successfully",
        message=f"You have successfully added {new_user.full_name} to the system.",
        type='success'
    )
    
    return jsonify({
        "message": "User created successfully",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "fullName": new_user.full_name,
            "role": new_user.role.value
        }
    }), 201

@user_bp.route('/<int:user_id>', methods=['PATCH'])
@role_required([UserRole.ADMIN])
def update_user(user_id):
    """
    Toggle user active status (Admin only)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: The ID of the user to update
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            is_active:
              type: boolean
              example: false
    responses:
      200:
        description: User active status updated successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden (Admin only)
      404:
        description: User not found
    """
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'is_active' in data:
        user.is_active = data['is_active']
        
    db.session.commit()
    
    return jsonify({"message": "User updated successfully"})
@user_bp.route('/export', methods=['GET'])
@token_required
def export_user_data():
    """
    Export current user data (tickets, profile, comments) as JSON, CSV, or PDF
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - name: format
        in: query
        type: string
        enum: [json, csv, pdf]
        default: json
        description: Export format
    responses:
      200:
        description: Exported data in requested format
      401:
        description: Unauthorized
    """
    format_type = request.args.get('format', 'json')
    user = g.user
    
    # 1. Fetch Data
    tickets = []
    from app.models.ticket import Ticket
    from app.core.constants import UserRole
    
    if user.role == UserRole.EMPLOYEE:
        tickets = Ticket.query.filter_by(created_by_id=user.id).all()
    elif user.role == UserRole.IT_STAFF:
         if user.team_id:
            tickets = Ticket.query.filter_by(team_id=user.team_id).all()
         else:
            tickets = Ticket.query.filter_by(assigned_to_id=user.id).all()
    
    # Comments
    from app.models.comment import Comment
    comments = Comment.query.filter_by(user_id=user.id).all()
    
    # 2. Format Data
    export_data = {
        "user": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "role": user.role.value,
            "joined": user.created_at.isoformat() if user.created_at else None
        },
        "tickets": [{
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "priority": t.priority.value,
            "category": t.category,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        } for t in tickets],
        "comments": [{
            "id": c.id,
            "ticket_id": c.ticket_id,
            "text": c.text,
            "created_at": c.created_at.isoformat()
        } for c in comments],
        "exported_at": datetime.utcnow().isoformat()
    }
    
    if format_type == 'csv':
        import csv
        import io
        from flask import make_response
        
        si = io.StringIO()
        cw = csv.writer(si)
        
        # Write User Info
        cw.writerow(['User Profile'])
        cw.writerow(['Name', user.full_name])
        cw.writerow(['Email', user.email])
        cw.writerow(['Role', user.role.value])
        cw.writerow([])
        
        # Write Tickets
        cw.writerow(['Tickets'])
        cw.writerow(['ID', 'Title', 'Status', 'Priority', 'Category', 'Created At'])
        for t in tickets:
            cw.writerow([t.id, t.title, t.status.value, t.priority.value, t.category, t.created_at])
        cw.writerow([])

        # Write Comments
        cw.writerow(['My Comments'])
        cw.writerow(['Ticket ID', 'Comment', 'Date'])
        for c in comments:
            cw.writerow([c.ticket_id, c.text, c.created_at])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=ticket_tally_data_{user.id}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    if format_type == 'pdf':
        from flask import send_file
        from app.services.pdf_service import PDFService
        
        pdf_buffer = PDFService.generate_user_report(user, tickets, comments)
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"ticket_tally_report_{user.id}.pdf",
            mimetype='application/pdf'
        )

    return jsonify(export_data)

@user_bp.route('/agents', methods=['GET'])
@token_required
def get_agents():
    """
    Get list of active IT support agents
    """
    search_query = request.args.get('search')
    specialty_filter = request.args.get('specialty')
    
    from app.core.config import Config
    query = User.query.filter(
        User.role.in_([UserRole.IT_STAFF, UserRole.ADMIN]),
        User.is_active == True,
        User.email != Config.DEMO_EMAIL
    )
    
    agents = query.all()
    
    filtered_agents = []
    for agent in agents:
        specs = agent.specializations or []
        
        # Match specialty filter
        if specialty_filter:
            if specialty_filter.lower() not in [s.lower() for s in specs]:
                continue
                
        # Match search query (searches name, email, team name, and specializations)
        if search_query:
            search_lower = search_query.lower()
            team_name = agent.team.name.lower() if agent.team else ""
            match_name = search_lower in agent.full_name.lower()
            match_email = search_lower in agent.email.lower()
            match_team = search_lower in team_name
            match_spec = any(search_lower in s.lower() for s in specs)
            
            if not (match_name or match_email or match_team or match_spec):
                continue
                
        filtered_agents.append(agent)
        
    return jsonify([{
        "id": a.id,
        "email": a.email,
        "fullName": a.full_name,
        "full_name": a.full_name,
        "role": a.role.value,
        "department": a.department,
        "team": {
            "id": a.team.id,
            "name": a.team.name
        } if a.team else None,
        "specializations": a.specializations or []
    } for a in filtered_agents])

@user_bp.route('/specialties', methods=['GET'])
@token_required
def get_all_specialties():
    """
    Get list of all unique specialties/specializations across all active agents
    """
    from app.core.config import Config
    agents = User.query.filter(
        User.role.in_([UserRole.IT_STAFF, UserRole.ADMIN]),
        User.is_active == True,
        User.email != Config.DEMO_EMAIL
    ).all()
    
    specialties_set = set()
    for agent in agents:
        if agent.specializations:
            for s in agent.specializations:
                if s.strip():
                    specialties_set.add(s.strip())
                    
    return jsonify(sorted(list(specialties_set)))

@user_bp.route('/teams', methods=['GET'])
@token_required
def get_all_teams():
    """
    Get list of all teams in the system (for directory dropdown)
    """
    from app.models.team import Team
    teams = Team.query.all()
    return jsonify([{
        "id": t.id,
        "name": t.name
    } for t in teams])
