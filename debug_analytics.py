from app.main import create_app
from app.core.database import db
from app.models.user import User
from app.core.constants import UserRole
from app.utils.jwt import create_access_token
import requests
import json
import os

BASE_URL = "http://127.0.0.1:5000"

def get_it_token():
    app = create_app()
    with app.app_context():
        # Find an IT Staff user
        user = User.query.filter_by(role=UserRole.IT_STAFF).first()
        if not user:
            print("No IT Staff user found!")
            return None, None
            
        from app.core.config import Config
        print(f"DEBUG: JWT_SECRET_KEY starts with {Config.JWT_SECRET_KEY[:3] if Config.JWT_SECRET_KEY else 'None'}")
        token = create_access_token(identity=str(user.id))
        return token, user.email

def check_analytics(token):
    print(f"Checking analytics with token...")
    url = f"{BASE_URL}/api/v1/analytics/it-dashboard"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Analytics failed: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("Connection Refused. Is the app running?")

def create_dummy_ticket(user_email):
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=user_email).first()
        if not user: return
        
        from app.models.ticket import Ticket
        from app.core.constants import TicketStatus, TicketPriority
        import datetime
        from app.core.database import db
        
        # Check if dummy exists
        existing = Ticket.query.filter_by(title="Weekly Chart Test Ticket").first()
        if not existing:
            t = Ticket(
                title="Weekly Chart Test Ticket",
                description="Testing the weekly performance chart.",
                category="IT Support",
                status=TicketStatus.OPEN,
                priority=TicketPriority.HIGH,
                created_by_id=user.id,
                assigned_to_id=user.id, # Assign to self to show in "Assigned"
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
            db.session.add(t)
            db.session.commit()
            print("Created dummy ticket for testing.")
        else:
            # Update created_at to NOW to ensure it shows up
            existing.created_at = datetime.datetime.utcnow()
            existing.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            print("Updated existing dummy ticket time.")

if __name__ == "__main__":
    token, email = get_it_token()
    if token:
        print(f"Generated token for {email}")
        create_dummy_ticket(email)
        check_analytics(token)

