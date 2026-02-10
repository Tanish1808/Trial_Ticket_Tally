from app.main import create_app
from app.core.database import db
from app.models.user import User
from app.models.team import Team
from app.services.auth_service import AuthService
from app.schemas.auth_schema import SignupRequest
from werkzeug.security import generate_password_hash
from app.core.constants import UserRole

# Create app context
app = create_app()

with app.app_context():
    print("starting simulation...")
    
    # 1. Clean up potential previous test data
    User.query.filter(User.email.in_(['test_emp@demo.com', 'test_it@demo.com'])).delete()
    db.session.commit()

    # 2. Simulate User Signup (Employee with Department)
    print("\nSimulating Employee Signup...")
    try:
        signup_data = SignupRequest(
            email='test_emp@demo.com',
            password='password123',
            full_name='Test Employee',
            role=UserRole.EMPLOYEE,
            department='Engineering' # Field to verify
        )
        user = AuthService.register_user(signup_data)
        print(f"Created User: {user.full_name}, Role: {user.role.value}, Department: {user.department}")
    except Exception as e:
        print(f"Signup Failed: {e}")

    # 3. Simulate Admin Adding IT Staff with Team
    print("\nSimulating Add IT Staff...")
    
    # Ensure team exists
    team = Team.query.filter_by(name='Software Team').first()
    if not team:
        team = Team(name='Software Team')
        db.session.add(team)
        db.session.commit()
        print("Created 'Software Team'")
    
    # Create IT Staff via direct model (simulating route logic)
    it_user = User(
        email='test_it@demo.com',
        full_name='Test IT Staff',
        role=UserRole.IT_STAFF,
        password_hash=generate_password_hash('password123'),
        team_id=team.id,
        is_active=True
    )
    db.session.add(it_user)
    db.session.commit()
    print(f"Created IT Staff: {it_user.full_name}, Role: {it_user.role.value}, Team: {it_user.team.name}")

    # 4. Verify Data Fetching
    print("\nVerifying Data Fetching...")
    
    # Fetch Employees
    employees = User.query.filter_by(role=UserRole.EMPLOYEE).all()
    print(f"Employees Found: {len(employees)}")
    for emp in employees:
         if emp.email == 'test_emp@demo.com':
             print(f"  - Verified: {emp.full_name} | Dept: {emp.department}")

    # Fetch IT Staff
    staff = User.query.filter_by(role=UserRole.IT_STAFF).all()
    print(f"IT Staff Found: {len(staff)}")
    for s in staff:
        if s.email == 'test_it@demo.com':
            print(f"  - Verified: {s.full_name} | Team: {s.team.name}")
            
    print("\nSimulation Complete.")
