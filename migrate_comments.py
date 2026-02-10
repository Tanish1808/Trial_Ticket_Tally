
import os
from app.main import create_app
from app.core.database import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Check if column exists
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(comments)"))
            columns = [row[1] for row in result]
            
            if 'parent_id' not in columns:
                print("Adding parent_id column to comments table...")
                conn.execute(text("ALTER TABLE comments ADD COLUMN parent_id INTEGER REFERENCES comments(id)"))
                conn.commit()
                print("Column added successfully.")
            else:
                print("Column parent_id already exists.")
                
    except Exception as e:
        print(f"Error: {e}")
