import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.team import Team
from app.models.team_mapping import TeamMapping
from app.core.constants import UserRole, TicketPriority
from app.schemas.ticket_schema import TicketCreate
from app.services.ticket_service import TicketService
from app.utils.jwt import create_access_token

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Seed teams required for testing
        it_team = Team(name="IT Support")
        software_team = Team(name="Software Team")
        db.session.add_all([it_team, software_team])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def admin_headers(app):
    admin = User(
        email="admin_test@tt.com",
        password_hash="test",
        full_name="Admin Test",
        role=UserRole.ADMIN
    )
    db.session.add(admin)
    db.session.commit()
    token = create_access_token(identity=str(admin.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def employee_headers(app):
    user = User(
        email="employee_test@tt.com",
        password_hash="test",
        full_name="Employee Test",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}

def test_ticket_routing_with_mapping(app):
    soft_team = Team.query.filter_by(name="Software Team").first()
    mapping = TeamMapping(category="Custom Software Category", team_id=soft_team.id)
    db.session.add(mapping)
    
    employee = User(
        email="employee_test2@tt.com",
        password_hash="test",
        full_name="Employee Test 2",
        role=UserRole.EMPLOYEE
    )
    db.session.add(employee)
    db.session.commit()

    ticket_data = TicketCreate(
        title="Software bug",
        description="Help me",
        category="Custom Software Category",
        priority=TicketPriority.LOW
    )
    ticket = TicketService.create_ticket(ticket_data, employee.id)
    assert ticket.team_id == soft_team.id

def test_ticket_routing_fallback(app):
    employee = User(
        email="employee_test3@tt.com",
        password_hash="test",
        full_name="Employee Test 3",
        role=UserRole.EMPLOYEE
    )
    db.session.add(employee)
    db.session.commit()

    ticket_data = TicketCreate(
        title="Strange issue",
        description="Help me",
        category="Some Random Category",
        priority=TicketPriority.LOW
    )
    ticket = TicketService.create_ticket(ticket_data, employee.id)
    
    it_support = Team.query.filter_by(name="IT Support").first()
    assert ticket.team_id == it_support.id

def test_admin_get_team_mappings(client, admin_headers):
    response = client.get('/api/v1/admin/team-mappings', headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 0

def test_admin_crud_team_mapping(client, admin_headers):
    soft_team = Team.query.filter_by(name="Software Team").first()
    
    create_data = {"category": "Testing Category", "team_id": soft_team.id}
    res_create = client.post('/api/v1/admin/team-mappings', json=create_data, headers=admin_headers)
    assert res_create.status_code == 201
    created_map = res_create.get_json()
    assert created_map['category'] == "Testing Category"
    assert created_map['team_id'] == soft_team.id
    
    mapping_id = created_map['id']
    
    res_get = client.get('/api/v1/admin/team-mappings', headers=admin_headers)
    assert res_get.status_code == 200
    mappings = res_get.get_json()
    assert len(mappings) == 1
    assert mappings[0]['category'] == "Testing Category"
    
    it_team = Team.query.filter_by(name="IT Support").first()
    update_data = {"category": "Updated Testing Category", "team_id": it_team.id}
    res_update = client.put(f'/api/v1/admin/team-mappings/{mapping_id}', json=update_data, headers=admin_headers)
    assert res_update.status_code == 200
    updated_map = res_update.get_json()
    assert updated_map['category'] == "Updated Testing Category"
    assert updated_map['team_id'] == it_team.id
    
    res_del = client.delete(f'/api/v1/admin/team-mappings/{mapping_id}', headers=admin_headers)
    assert res_del.status_code == 200
    
    res_get_after = client.get('/api/v1/admin/team-mappings', headers=admin_headers)
    assert len(res_get_after.get_json()) == 0

def test_admin_crud_team_mapping_unauthorized(client, employee_headers):
    response = client.get('/api/v1/admin/team-mappings', headers=employee_headers)
    assert response.status_code == 403
    
    response_post = client.post('/api/v1/admin/team-mappings', json={"category": "Test", "team_id": 1}, headers=employee_headers)
    assert response_post.status_code == 403

def test_admin_create_invalid_team(client, admin_headers):
    create_data = {"category": "Testing Category", "team_id": 9999}
    res_create = client.post('/api/v1/admin/team-mappings', json=create_data, headers=admin_headers)
    assert res_create.status_code == 400
    assert "Target team not found" in res_create.get_json()['error']
