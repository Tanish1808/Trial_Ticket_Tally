from app.main import create_app
from app.core.database import db
from app.models.user import User

app = create_app()
with app.app_context():
    users = User.query.all()
    with open('dump.txt', 'w') as f:
        f.write(f"Total Users: {len(users)}\n")
        for u in users:
            f.write(f"ID:{u.id} | Name:{u.full_name} | Email:{u.email} | Active:{u.is_active}\n")
