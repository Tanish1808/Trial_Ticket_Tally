from app.main import create_app
from app.core.database import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Create any missing tables (e.g. messages)
    # Ensure models are imported
    from app.models.message import Message
    print("Creating missing tables...")
    db.create_all()
    print("Database update complete.")
