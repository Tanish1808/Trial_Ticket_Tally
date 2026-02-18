from app.core.database import db
from app.models.user import User
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token
from app.schemas.auth_schema import SignupRequest, LoginRequest
from app.services.email_service import EmailService
from datetime import datetime

class AuthService:
    @staticmethod
    def register_user(data: SignupRequest) -> User:
        # Normalize email
        normalized_email = data.email.lower().strip()
        
        # Check if user exists
        if User.query.filter_by(email=normalized_email).first():
            raise ValueError("Email already registered")
        
        # Create user
        new_user = User(
            email=normalized_email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            department=data.department,
            role=data.role,
            team_id=data.team_id
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Send welcome email (async ideally, but sync for now)
        from app.services.email_templates import get_signup_email
        email_body = get_signup_email(new_user.full_name)
        
        EmailService.send_email(
            new_user.email, 
            "Welcome to Ticket-Tally! 🚀", 
            email_body
        )
        
        return new_user

    @staticmethod
    def login_user(data: LoginRequest) -> dict:
        normalized_email = data.email.lower().strip()
        user = User.query.filter_by(email=normalized_email).first()
        
        if not user or not verify_password(user.password_hash, data.password):
            raise ValueError("Invalid credentials")
        
        if not user.is_active:
            raise ValueError("Account disabled")

        # Generate Token
        token = create_access_token(identity=str(user.id))
        
        return {
            "access_token": token,
            "user": user
        }

    @staticmethod
    def initiate_password_reset(email: str):
        user = User.query.filter_by(email=email).first()
        if user:
            from app.utils.token import generate_reset_token
            from app.services.notification_service import NotificationService
            
            token = generate_reset_token(user.email)
            NotificationService.notify_password_reset(user, token)
            
        # We return True even if user not found to prevent enumeration
        return True

    @staticmethod
    def complete_password_reset(token: str, new_password: str):
        from app.utils.token import verify_reset_token
        
        email = verify_reset_token(token)
        if not email:
            raise ValueError("Invalid or expired token")
            
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("User not found")
            
        user.password_hash = hash_password(new_password)
        db.session.commit()
        
        return True

    @staticmethod
    def get_or_create_demo_user() -> User:
        from app.core.config import Config
        from app.core.constants import UserRole
        
        user = User.query.filter_by(email=Config.DEMO_EMAIL).first()
        if not user:
            user = User(
                email=Config.DEMO_EMAIL,
                password_hash=hash_password(Config.DEMO_PASSWORD),
                full_name="Demo Employee",
                role=UserRole.EMPLOYEE,
                department="Sales",
                is_active=True
            )
            db.session.add(user)
        else:
            # Ensure role is updated to EMPLOYEE if it was previously ADMIN
            user.role = UserRole.EMPLOYEE
            user.full_name = "Demo Employee"
            
        db.session.commit()
            
        # Ensure sample tickets exist for demo user
        from app.models.ticket import Ticket
        from app.models.team import Team
        from app.core.constants import TicketStatus, TicketPriority
        
        # Get or Create Teams
        it_team = Team.query.filter_by(name="IT Support").first()
        if not it_team:
            it_team = Team(name="IT Support")
            db.session.add(it_team)
            
        hr_team = Team.query.filter_by(name="Human Resources").first()
        if not hr_team:
            hr_team = Team(name="Human Resources")
            db.session.add(hr_team)
            
        # Commit to get IDs
        db.session.commit()
        
        # CLEAR existing tickets for demo user to ensure clean state
        existing_tickets = Ticket.query.filter_by(created_by_id=user.id).all()
        for t in existing_tickets:
            db.session.delete(t)
        db.session.commit()
        
        # Create fresh sample tickets
        sample_tickets = [
            Ticket(
                title="VPN Access Issue", 
                description="Unable to connect to company VPN from home network. Error code 403.",
                category="Network Issue",
                priority=TicketPriority.HIGH,
                status=TicketStatus.OPEN,
                created_by_id=user.id,
                assigned_to_id=user.id,
                team_id=it_team.id,
                is_demo=True,
                created_at=datetime.utcnow()
            ),
            Ticket(
                title="Outlook Sync Error", 
                description="Emails are not syncing on my desktop client. Webmail works fine.",
                category="Email Issue",
                priority=TicketPriority.MEDIUM,
                status=TicketStatus.IN_PROGRESS,
                created_by_id=user.id,
                assigned_to_id=user.id,
                team_id=it_team.id,
                is_demo=True,
                created_at=datetime.utcnow()
            ),
            Ticket(
                title="Payroll Discrepancy", 
                description="My payslip for this month shows incorrect deduction.",
                category="Payroll",
                priority=TicketPriority.HIGH,
                status=TicketStatus.OPEN,
                created_by_id=user.id,
                assigned_to_id=user.id,
                team_id=hr_team.id,
                is_demo=True,
                created_at=datetime.utcnow()
            )
        ]
        db.session.add_all(sample_tickets)
        db.session.commit()
            
        return user

    @staticmethod
    def login_demo_user() -> dict:
        user = AuthService.get_or_create_demo_user()
        token = create_access_token(identity=str(user.id))
        return {
            "access_token": token,
            "user": user
        }
