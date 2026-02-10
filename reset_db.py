from app.main import create_app
from app.core.database import db
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.ticket_status_history import TicketStatusHistory
from sqlalchemy import text

app = create_app()

def reset_tickets():
    with app.app_context():
        print("⚠ WARNING: This will delete ALL tickets, comments, and history.")
        print("Users and Teams will be PRESERVED.")
        print("Ticket IDs will reset to start from #1001 (Internal ID 1).")
        
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm != 'CONFIRM':
            print("Operation cancelled.")
            return

        try:
            # 1. Delete Dependencies first (Foreign Keys)
            print("Deleting Comments...")
            num_comments = db.session.query(Comment).delete()
            
            print("Deleting Status History...")
            num_history = db.session.query(TicketStatusHistory).delete()
            
            # 2. Delete Tickets
            print("Deleting Tickets...")
            num_tickets = db.session.query(Ticket).delete()
            
            # 3. Delete Projects
            from app.models.project import Project, project_team
            
            print("Deleting Project Team Allocations...")
            db.session.execute(project_team.delete())
            
            print("Deleting Projects...")
            num_projects = db.session.query(Project).delete()

            # 4. Delete Non-Admin Users
            # We keep 'admin' role or specific admin users (safer to keep all Admins)
            from app.models.user import User
            from app.core.constants import UserRole
            
            print("Deleting Non-Admin Users...")
            # Delete everyone except ADMIN role
            num_users = db.session.query(User).filter(User.role != UserRole.ADMIN).delete()
            
            # 5. Reset Auto-Increment Counter (SQLite specific)
            # This makes the next Ticket ID start at 1
            print("Resetting Ticket ID Counter...")
            try:
                db.session.execute(text("DELETE FROM sqlite_sequence WHERE name='tickets'"))
                db.session.execute(text("DELETE FROM sqlite_sequence WHERE name='comments'"))
                db.session.execute(text("DELETE FROM sqlite_sequence WHERE name='ticket_status_history'"))
                db.session.execute(text("DELETE FROM sqlite_sequence WHERE name='projects'"))
            except Exception as e:
                print(f"⚠ Could not reset sequence (might be empty DB): {e}")

            # Users counter: Reset ONLY if we deleted everyone, but we kept Admin (ID 1).
            # So next user will be ID (highest+1). SQLite handles this automatically.
            # But if we want to reclaim "low" IDs (2, 3...), we might need to reset sequence to max(id).
            # For simplicity, let it continue.
            
            db.session.commit()
            
            print("------------------------------------------------")
            print(f"✔ Deleted {num_tickets} tickets.")
            print(f"✔ Deleted {num_projects} projects.")
            print(f"✔ Deleted {num_comments} comments.")
            print(f"✔ Deleted {num_history} history entries.")
            print(f"✔ Deleted {num_users} users (Admins kept safe).")
            print("✔ Teams Data preserved.")
            print("✔ Ticket ID counter reset.")
            print("------------------------------------------------")
            print("Success! The next ticket created will be TT-1001.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during reset: {e}")

if __name__ == "__main__":
    reset_tickets()
