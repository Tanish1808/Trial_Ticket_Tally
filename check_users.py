from app.main import create_app
from app.core.database import db
from app.models.user import User

app = create_app()

with app.app_context():
    # Check for 'test' in email or full_name
    users = User.query.filter(
        (User.email.ilike('%test%')) | 
        (User.full_name.ilike('%test%'))
    ).all()
    
    print("--- Found Test Users ---")
    for u in users:
        print(f"ID: {u.id} | Email: {u.email} | Name: {u.full_name} | Role: {u.role}")
    
    if not users:
        print("No users found with 'test' in email or name.")
