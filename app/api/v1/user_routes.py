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
    return jsonify({
        "id": g.user.id,
        "full_name": g.user.full_name,
        "email": g.user.email,
        "role": g.user.role.value,
        "department": g.user.department,
        "team_id": g.user.team_id,
        "preferences": g.user.preferences or {},
        "created_at": g.user.created_at.isoformat() if g.user.created_at else None
    })

@user_bp.route('/me', methods=['PATCH'])
@token_required
def update_my_profile():
    data = request.get_json()
    
    # Only allow updating specific fields
    if 'full_name' in data:
        g.user.full_name = data['full_name']
        
    if 'department' in data and g.user.role == UserRole.EMPLOYEE:
        g.user.department = data['department']

    if 'preferences' in data:
        # Ensure it's a dict
        if isinstance(data['preferences'], dict):
            # We must assign a NEW dictionary to trigger SQLAlchemy detection for JSON types
            current_prefs = dict(g.user.preferences) if g.user.preferences else {}
            current_prefs.update(data['preferences'])
            g.user.preferences = current_prefs

    db.session.commit()
    
    return jsonify({
        "message": "Profile updated successfully",
        "user": {
            "id": g.user.id,
            "full_name": g.user.full_name,
            "email": g.user.email,
            "role": g.user.role.value,
            "department": g.user.department
        }
    })

@user_bp.route('/me/password', methods=['POST'])
@token_required
def change_my_password():
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
        "role": u.role.value,
        "department": u.department,
        "team": u.team.name if u.team else None,
        "tickets_raised": len(u.created_tickets),
        "tickets_resolved": sum(1 for t in u.assigned_tickets if t.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]),
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None
    } for u in users])

@user_bp.route('', methods=['POST'])
@role_required([UserRole.ADMIN])
def create_user():
    data = request.get_json()
    
    email = data.get('email', '').lower().strip()
    password = data.get('password', 'password123') # Default password
    full_name = data.get('full_name')
    role_str = data.get('role', 'employee')
    team_name = data.get('team')
    
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
        is_active=True
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
            "role": new_user.role.value
        }
    }), 201

@user_bp.route('/<int:user_id>', methods=['PATCH'])
@role_required([UserRole.ADMIN])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'is_active' in data:
        user.is_active = data['is_active']
        
    db.session.commit()
    
    return jsonify({"message": "User updated successfully"})
@user_bp.route('/export', methods=['GET'])
@token_required
def export_user_data():
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
