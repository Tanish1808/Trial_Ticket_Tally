import sqlite3
import os

# Try to find the DB file
db_path = 'ticket_tally.db'
if not os.path.exists(db_path):
    # Check instance folder
    db_path = os.path.join('instance', 'ticket_tally.db')

if not os.path.exists(db_path):
    print(f"Error: Could not find database file at {db_path} or in root.")
    # Fallback to hardcoded path found in previous steps if Find tool returns something else
    # For now, we will print error.
else:
    print(f"Found database at: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'preferences' in columns:
            print("Column 'preferences' already exists.")
        else:
            print("Adding 'preferences' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN preferences JSON DEFAULT '{}'")
            conn.commit()
            print("Column added successfully.")
            
        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")
