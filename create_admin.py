import sys
import os

# Ensure root is in path
sys.path.append(os.getcwd())

from app.main import create_app
from app.core.database import db
from app.models.user import User
from app.core.constants import UserRole
from app.utils.password import hash_password

def create_admin():
    app = create_app()
    with app.app_context():
        email = "a79321035@gmail.com"
        password = "admin@tt"
        
        existing_admin = User.query.filter_by(email=email).first()
        if existing_admin:
            print(f"Admin user {email} already exists.")
            return

        print(f"Creating admin user {email}...")
        admin = User(
            email=email,
            password_hash=hash_password(password),
            full_name="System Admin",
            role=UserRole.ADMIN
        )
        
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully.")

if __name__ == "__main__":
    create_admin()
