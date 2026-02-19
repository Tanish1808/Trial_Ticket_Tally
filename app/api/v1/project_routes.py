from flask import Blueprint, jsonify, g, request
from app.models.project import Project
from app.models.user import User
from app.core.database import db
from app.middleware.auth_middleware import token_required, role_required
from app.core.constants import UserRole, ProjectStatus, TicketPriority
from datetime import datetime

project_bp = Blueprint('projects', __name__, url_prefix='/api/v1/projects')

@project_bp.route('', methods=['GET'])
@token_required
def get_projects():
    projects = Project.query.all()
    return jsonify([p.to_dict() for p in projects])

@project_bp.route('', methods=['POST'])
@role_required([UserRole.ADMIN])
def create_project():
    data = request.get_json()
    
    try:
        new_project = Project(
            name=data['name'],
            description=data.get('description'),
            status=ProjectStatus(data['status']),
            priority=TicketPriority(data['priority']),
            start_date=datetime.strptime(data['startDate'], '%Y-%m-%d').date() if data.get('startDate') else None,
            deadline=datetime.strptime(data['deadline'], '%Y-%m-%d').date() if data.get('deadline') else None,
            progress=data.get('progress', 0),
            created_by_id=g.user.id
        )
        
        # Handle Team
        if 'team' in data:
            for member_data in data['team']:
                identifier = member_data.get('email') or member_data.get('name')
                if identifier:
                    # Try email first
                    user = User.query.filter_by(email=identifier).first()
                    # If not found, try full name
                    if not user:
                         user = User.query.filter(User.full_name.ilike(identifier)).first()
                    
                    if user:
                        new_project.team.append(user)
        
        db.session.add(new_project)
        db.session.commit()
        
        # Send Email Notifications
        try:
            from app.services.email_service import EmailService
            from app.services.email_templates import get_project_created_email, get_project_assignment_email
            
            # 1. Notify Admin (Creator)
            admin_email_body = get_project_created_email(
                name=g.user.full_name,
                project_name=new_project.name,
                start_date=new_project.start_date.strftime('%Y-%m-%d') if new_project.start_date else 'N/A',
                deadline=new_project.deadline.strftime('%Y-%m-%d') if new_project.deadline else 'N/A'
            )
            
            EmailService.send_email(
                g.user.email,
                f"Project Created - {new_project.name} 🚀",
                admin_email_body
            )
            
            # 2. Notify Assigned Team Members
            for member in new_project.team:
                # Skip if member is the creator (though usually they are different roles, just in case)
                if member.id == g.user.id:
                    continue
                    
                member_email_body = get_project_assignment_email(
                    name=member.full_name,
                    project_name=new_project.name,
                    role="Team Member", # detailed role not in Many-to-Many, generic "Team Member"
                    start_date=new_project.start_date.strftime('%Y-%m-%d') if new_project.start_date else 'N/A',
                    deadline=new_project.deadline.strftime('%Y-%m-%d') if new_project.deadline else 'N/A'
                )
                
                EmailService.send_email(
                    member.email,
                    f"New Project Assignment - {new_project.name} 📋",
                    member_email_body
                )
                
        except Exception as e:
            print(f"Failed to send project emails: {e}")
        
        return jsonify(new_project.to_dict()), 201
        
    except KeyError as e:
        return jsonify({"error": f"Missing field: {str(e)}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@project_bp.route('/<int:project_id>', methods=['GET'])
@token_required
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    return jsonify(project.to_dict())

@project_bp.route('/<int:project_id>', methods=['PATCH'])
@role_required([UserRole.ADMIN])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    
    # [NEW] Prevent editing completed projects
    if project.status == ProjectStatus.COMPLETED:
        # Check if we are reopening the project (changing status away from COMPLETED)
        # If the user allows reopening, we might check 'status' in data.
        # But strictly following "cannot change a single field", we block it.
        # However, to avoid "stuck" projects, we usually allow waiting to Active.
        # For this request, I will strictly block ALL content updates.
        # If 'status' is changing TO something else, we allow it?
        # The user said "Admin can not Change a Single field in Edit Peoject".
        # This implies the state is "Frozen".
        return jsonify({"error": "Cannot edit a completed project"}), 400

    if 'name' in data:
        project.name = data['name']
    if 'description' in data:
        project.description = data['description']
    if 'status' in data:
        new_status = ProjectStatus(data['status'])
        # Prevent reverting completed projects
        if project.status == ProjectStatus.COMPLETED and new_status != ProjectStatus.COMPLETED:
            return jsonify({"error": "Cannot change status of a completed project"}), 400
        project.status = new_status
    if 'priority' in data:
        project.priority = TicketPriority(data['priority'])
    if 'startDate' in data:
        project.start_date = datetime.strptime(data['startDate'], '%Y-%m-%d').date() if data['startDate'] else None
    if 'deadline' in data:
        project.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date() if data['deadline'] else None
    if 'progress' in data:
        project.progress = int(data['progress'])
        
    # Handle Team Update
    if 'team' in data:
        # 1. Capture existing members specific IDs
        existing_member_ids = {u.id for u in project.team}
        
        project.team = [] # Clear existing
        for member_data in data['team']:
            identifier = member_data.get('email') or member_data.get('name')
            if identifier:
                # Try email first
                user = User.query.filter_by(email=identifier).first()
                # If not found, try full name
                if not user:
                        user = User.query.filter(User.full_name.ilike(identifier)).first()
                
                if user:
                    project.team.append(user)
        
        db.session.commit()

        # 2. Identify and Notify New Members
        try:
            from app.services.email_service import EmailService
            from app.services.email_templates import get_project_assignment_email
            
            for member in project.team:
                if member.id not in existing_member_ids and member.id != g.user.id:
                    member_email_body = get_project_assignment_email(
                        name=member.full_name,
                        project_name=project.name,
                        role="Team Member",
                        start_date=project.start_date.strftime('%Y-%m-%d') if project.start_date else 'N/A',
                        deadline=project.deadline.strftime('%Y-%m-%d') if project.deadline else 'N/A'
                    )
                    
                    EmailService.send_email(
                        member.email,
                        f"New Project Assignment - {project.name} 📋",
                        member_email_body
                    )
        except Exception as e:
            print(f"Failed to send assignment emails during update: {e}")
            
    else:
        db.session.commit()

    return jsonify(project.to_dict())

@project_bp.route('/<int:project_id>', methods=['DELETE'])
@role_required([UserRole.ADMIN])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted successfully"})
