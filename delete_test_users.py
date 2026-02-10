from app.main import create_app
from app.core.database import db
from app.models.user import User

app = create_app()
with app.app_context():
    targets = ['New Hire', 'Deactivated User']
    for t in targets:
        users = User.query.filter((User.full_name.ilike(f'%{t}%')) | (User.email.ilike(f'%{t}%'))).all()
        for u in users:
            print(f"Deleting user: {u.full_name} ({u.email})")
            db.session.delete(u)
    db.session.commit()
    print("Cleanup complete.")
