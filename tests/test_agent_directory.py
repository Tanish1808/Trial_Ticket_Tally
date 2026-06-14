import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.team import Team
from app.models.ticket import Ticket
from app.core.constants import UserRole, TicketPriority, TicketStatus
from app.utils.jwt import create_access_token
from app.schemas.ticket_schema import TicketCreate
from app.services.ticket_service import TicketService

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Seed teams
        team1 = Team(name="Hardware Support")
        team2 = Team(name="Network Operations")
        db.session.add_all([team1, team2])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def employee_headers(app):
    emp = User(
        email="emp_dir@tt.com",
        password_hash="test",
        full_name="Employee Directory",
        role=UserRole.EMPLOYEE
    )
    db.session.add(emp)
    db.session.commit()
    token = create_access_token(identity=str(emp.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def agent_headers(app):
    team = Team.query.filter_by(name="Hardware Support").first()
    agent = User(
        email="agent_dir@tt.com",
        password_hash="test",
        full_name="Agent Directory",
        role=UserRole.IT_STAFF,
        team_id=team.id
    )
    db.session.add(agent)
    db.session.commit()
    token = create_access_token(identity=str(agent.id))
    return {"Authorization": f"Bearer {token}"}

def test_agent_update_specialties(client, agent_headers, app):
    # Set specialties on self
    payload = {
        "full_name": "Agent Directory Updated",
        "specializations": ["Network Security", "Hardware Diagnosis"]
    }
    response = client.patch('/api/v1/users/me', json=payload, headers=agent_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data['user']['full_name'] == "Agent Directory Updated"
    assert "Network Security" in data['user']['specializations']
    assert "Hardware Diagnosis" in data['user']['specializations']

    # Verify database
    with app.app_context():
        agent = User.query.filter_by(email="agent_dir@tt.com").first()
        assert agent.specializations == ["Network Security", "Hardware Diagnosis"]

def test_employee_cannot_update_specialties(client, employee_headers, app):
    payload = {
        "specializations": ["Hacked Spec"]
    }
    response = client.patch('/api/v1/users/me', json=payload, headers=employee_headers)
    assert response.status_code == 200
    data = response.get_json()
    # Should not include specializations because employee cannot update them
    assert "specializations" not in data['user']

    with app.app_context():
        emp = User.query.filter_by(email="emp_dir@tt.com").first()
        assert emp.specializations is None or len(emp.specializations) == 0

def test_get_agents_and_filtering(client, employee_headers, app):
    with app.app_context():
        hw_team = Team.query.filter_by(name="Hardware Support").first()
        net_team = Team.query.filter_by(name="Network Operations").first()

        # Create agents with specialties
        agent1 = User(
            email="ag1@tt.com",
            password_hash="test",
            full_name="Alice Specialist",
            role=UserRole.IT_STAFF,
            team_id=hw_team.id,
            specializations=["Laptops", "Printers", "Hardware"]
        )
        agent2 = User(
            email="ag2@tt.com",
            password_hash="test",
            full_name="Bob Networker",
            role=UserRole.IT_STAFF,
            team_id=net_team.id,
            specializations=["VPN", "Routing", "Firewall"]
        )
        db.session.add_all([agent1, agent2])
        db.session.commit()

    # 1. Get all agents
    response = client.get('/api/v1/users/agents', headers=employee_headers)
    assert response.status_code == 200
    agents = response.get_json()
    # Should contain Alice and Bob (plus the fixture agent if exists)
    assert len(agents) >= 2

    # 2. Filter by specialty
    response_spec = client.get('/api/v1/users/agents?specialty=VPN', headers=employee_headers)
    assert response_spec.status_code == 200
    vpn_agents = response_spec.get_json()
    assert len(vpn_agents) == 1
    assert vpn_agents[0]['fullName'] == "Bob Networker"

    # 3. Filter by search query (name)
    response_search = client.get('/api/v1/users/agents?search=Alice', headers=employee_headers)
    assert response_search.status_code == 200
    search_agents = response_search.get_json()
    assert len(search_agents) == 1
    assert search_agents[0]['fullName'] == "Alice Specialist"

    # 4. Filter by search query (specialty fuzzy match)
    response_fuzzy = client.get('/api/v1/users/agents?search=Print', headers=employee_headers)
    assert response_fuzzy.status_code == 200
    fuzzy_agents = response_fuzzy.get_json()
    assert len(fuzzy_agents) == 1
    assert fuzzy_agents[0]['fullName'] == "Alice Specialist"

def test_get_all_specialties(client, employee_headers, app):
    with app.app_context():
        agent1 = User(
            email="ag1@tt.com",
            password_hash="test",
            full_name="Alice Specialist",
            role=UserRole.IT_STAFF,
            specializations=["Laptops", "Printers"]
        )
        agent2 = User(
            email="ag2@tt.com",
            password_hash="test",
            full_name="Bob Networker",
            role=UserRole.IT_STAFF,
            specializations=["VPN", "Laptops"]
        )
        db.session.add_all([agent1, agent2])
        db.session.commit()

    response = client.get('/api/v1/users/specialties', headers=employee_headers)
    assert response.status_code == 200
    specialties = response.get_json()
    # Should return unique and sorted list: ["Laptops", "Printers", "VPN"]
    assert specialties == ["Laptops", "Printers", "VPN"]

def test_get_all_teams(client, employee_headers):
    response = client.get('/api/v1/users/teams', headers=employee_headers)
    assert response.status_code == 200
    teams = response.get_json()
    assert len(teams) == 2
    team_names = [t['name'] for t in teams]
    assert "Hardware Support" in team_names
    assert "Network Operations" in team_names

def test_direct_ticket_assignment(client, employee_headers, app):
    with app.app_context():
        team = Team.query.filter_by(name="Hardware Support").first()
        agent = User(
            email="ag1@tt.com",
            password_hash="test",
            full_name="Alice Specialist",
            role=UserRole.IT_STAFF,
            team_id=team.id,
            specializations=["Laptops"]
        )
        db.session.add(agent)
        db.session.commit()
        agent_id = agent.id

    payload = {
        "title": "My screen is broken",
        "description": "Please help, it is completely black.",
        "category": "Hardware Issue",
        "priority": "High",
        "assigned_to_id": agent_id
    }
    
    response = client.post('/api/v1/tickets', json=payload, headers=employee_headers)
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == "Ticket created"
    ticket_id = data['ticket_id']

    # Verify in database that it was assigned to Alice and also mapped to her team
    with app.app_context():
        ticket = Ticket.query.get(ticket_id)
        assert ticket is not None
        assert ticket.assigned_to_id == agent_id
        assert ticket.team.name == "Hardware Support"
        assert ticket.status == TicketStatus.OPEN
