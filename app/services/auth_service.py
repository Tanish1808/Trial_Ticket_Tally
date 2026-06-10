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
        """Registers a new user in the system and sends a welcome email.

        Args:
            data (SignupRequest): User signup details (email, password, full_name, role, etc.).

        Returns:
            User: The newly created User database model instance.

        Raises:
            ValueError: If the email address is already registered.
        """
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
        """Authenticates a user and generates a JWT access token.

        Args:
            data (LoginRequest): User login credentials (email, password).

        Returns:
            dict: A dictionary containing the 'access_token' and 'user' object.

        Raises:
            ValueError: If credentials are invalid or if the account is deactivated.
        """
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
        """Initiates a password reset process by generating a token and sending an email.

        Args:
            email (str): The email address of the user requesting password reset.

        Returns:
            bool: True in all cases to prevent email/account enumeration attacks.
        """
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
        """Resets the password of a user using a valid password reset token.

        Args:
            token (str): The password reset token.
            new_password (str): The new password to set.

        Returns:
            bool: True if the password reset succeeds.

        Raises:
            ValueError: If the token is invalid/expired or if the user is not found.
        """
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
        """Retrieves the system-wide demo employee user, creating it and seeding sample tickets if absent.

        Returns:
            User: The demo User database model instance.
        """
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

        # Seed sample announcements for demo context
        from app.models.announcement import Announcement
        from datetime import timedelta

        # Clear existing announcements by the demo user to prevent duplication
        existing_announcements = Announcement.query.filter_by(created_by_id=user.id).all()
        for a in existing_announcements:
            db.session.delete(a)
        db.session.commit()

        # Add fresh sample announcements
        sample_announcements = [
            Announcement(
                title="Scheduled Database Maintenance ⚠️",
                message="The primary ticketing database will undergo scheduled maintenance this Sunday from 02:00 AM to 04:00 AM UTC. Some services might experience brief latency.",
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=5),
                created_by_id=user.id
            ),
            Announcement(
                title="Welcome to Ticket-Tally! 🎉",
                message="Welcome to the demo environment of the Ticket-Tally ITSM Platform. Explore ticket creation, the Kanban board, and calendar features. Share your feedback via the Contact form!",
                is_active=True,
                expires_at=None,
                created_by_id=user.id
            )
        ]
        db.session.add_all(sample_announcements)
        db.session.commit()
            
        return user

    @staticmethod
    def login_demo_user() -> dict:
        """Authenticates and logins the demo user, returning a JWT token.

        Returns:
            dict: A dictionary containing the 'access_token' and 'user' object.
        """
        user = AuthService.get_or_create_demo_user()
        token = create_access_token(identity=str(user.id))
        return {
            "access_token": token,
            "user": user
        }
