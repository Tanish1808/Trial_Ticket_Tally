from app.main import create_app
from app.core.database import db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.team import Team
from app.services.ticket_service import TicketService
from app.core.constants import UserRole, TicketStatus, TicketPriority
from datetime import datetime
from werkzeug.security import generate_password_hash

app = create_app()

def cleanup():
    print("--- Cleaning up previous test data ---")
    try:
        users = User.query.filter(User.email.like('test_%')).all()
        for u in users:
            Ticket.query.filter_by(created_by_id=u.id).delete()
            Ticket.query.filter_by(assigned_to_id=u.id).delete()
            db.session.delete(u)
        
        Ticket.query.filter(Ticket.title.like('Test Ticket %')).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Cleanup Error: {e}")

def run_simulation():
    with app.app_context():
        cleanup()
        print("\n--- Starting Simulation ---")

        # 1. Setup Teams and Users
        software_team = Team.query.filter_by(name='Software Team').first()
        if not software_team:
            software_team = Team(name='Software Team')
            db.session.add(software_team)
            db.session.commit()

        user_a = User(email='test_it_a@demo.com', full_name='IT Staff A', role=UserRole.IT_STAFF, team_id=software_team.id)
        user_a.password_hash = generate_password_hash('password')
        
        user_b = User(email='test_it_b@demo.com', full_name='IT Staff B', role=UserRole.IT_STAFF, team_id=software_team.id)
        user_b.password_hash = generate_password_hash('password')
        
        creator = User(email='test_emp@demo.com', full_name='Test Employee', role=UserRole.EMPLOYEE)
        creator.password_hash = generate_password_hash('password')

        db.session.add_all([user_a, user_b, creator])
        db.session.commit()

        # 2. Create Tickets
        tickets = []
        for i in range(1, 6):
            t = Ticket(
                title=f"Test Ticket {i}",
                description="Fix the bug",
                category="Software Issue",
                priority=TicketPriority.MEDIUM,
                created_by_id=creator.id,
                team_id=software_team.id,
                status=TicketStatus.OPEN
            )
            db.session.add(t)
            tickets.append(t)
        db.session.commit()

        # Reload tickets
        tickets = Ticket.query.filter(Ticket.title.like('Test Ticket %')).all()
        t1 = tickets[0]

        # 3. User A claims Ticket 1
        print(f"\n[Action] User A claiming Ticket {t1.id}...")
        try:
            TicketService.claim_ticket(t1.id, user_a.id)
            print("✅ Success: User A claimed Ticket 1")
            
            # Verify My Assignments
            print("[Verify] Checking My Assignments for User A...")
            my_tickets = Ticket.query.filter_by(assigned_to_id=user_a.id).all()
            found_ticket = next((t for t in my_tickets if t.id == t1.id), None)
            
            if found_ticket:
                print(f"✅ Success: Ticket {t1.id} is now in User A's assignments")
                print(f"   Status: {found_ticket.status.value}")
                
                # 4. User A updates Ticket 1 to Resolved
                print(f"\n[Action] User A updating Ticket {t1.id} to RESOLVED...")
                TicketService.update_ticket(t1.id, {"status": TicketStatus.RESOLVED}, user_a.id)
                db.session.commit()
                
                t1_resolved = Ticket.query.get(t1.id)
                if t1_resolved.status == TicketStatus.RESOLVED:
                    print("✅ Success: Ticket 1 updated to RESOLVED")
                else:
                    print(f"❌ Failed: Ticket 1 status is {t1_resolved.status}")

            else:
                print(f"❌ Failed: Ticket {t1.id} NOT found in User A's assignments")
                
        except Exception as e:
            print(f"❌ Failed: {e}")

        # Cleanup
        cleanup()
        print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    run_simulation()
