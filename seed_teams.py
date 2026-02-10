from app.main import create_app
from app.core.database import db
from app.models.team import Team

app = create_app()

with app.app_context():
    teams = ['Software Team', 'Hardware Team', 'Network Team', 'IT Support']
    for name in teams:
        target_team = Team.query.filter_by(name=name).first()
        if not target_team:
            print(f"Creating team: {name}")
            db.session.add(Team(name=name))
        else:
            print(f"Team exists: {name}")
    db.session.commit()
    print("Teams seeded successfully.")
