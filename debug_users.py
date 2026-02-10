from app.main import create_app
from app.core.database import db
from app.models.user import User

app = create_app()

with app.app_context():
    users = User.query.all()
    print("-" * 50)
    print(f"Total Users: {len(users)}")
    print("-" * 50)
    for user in users:
        print(f"ID: {user.id} | Name: {user.full_name} | Role: {user.role.value} | Email: {user.email}")
    print("-" * 50)
