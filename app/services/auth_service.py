from app.core.database import db
from app.models.user import User
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token
from app.schemas.auth_schema import SignupRequest, LoginRequest
from app.services.email_service import EmailService

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
