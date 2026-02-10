from app.main import create_app
from app.core.database import db
from app.models.ticket import Ticket
from app.models.team import Team

app = create_app()

def fix_assignments():
    with app.app_context():
        # Get all teams
        teams = Team.query.all()
        team_map = {t.name: t for t in teams}
        
        # Mapping logic (same as service)
        category_map = {
            'Software Issue': 'Software Team',
            'Hardware Issue': 'Hardware Team',
            'Network Issue': 'Network Team',
            'Email Issue': 'Software Team'
        }
        
        tickets = Ticket.query.filter((Ticket.team_id == None) | (Ticket.team_id == 0)).all()
        print(f"Found {len(tickets)} unassigned tickets.")
        
        count = 0
        for t in tickets:
            target_team_name = category_map.get(t.category, 'IT Support')
            target_team = team_map.get(target_team_name)
            
            if target_team:
                t.team = target_team
                t.team_id = target_team.id
                count += 1
                print(f"Assigned Ticket {t.id} ({t.category}) to {target_team.name}")
        
        if count > 0:
            db.session.commit()
            print(f"Successfully backfilled {count} tickets.")
        else:
            print("No tickets needed updates.")

if __name__ == "__main__":
    fix_assignments()
