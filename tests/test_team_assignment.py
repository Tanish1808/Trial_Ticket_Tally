import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.core.constants import UserRole
from app.utils.jwt import create_access_token

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
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

def test_team_assignment(client, admin_headers):
    # 1. Test Search
    response = client.get('/api/v1/users?search=Admin', headers=admin_headers)
    assert response.status_code == 200, f"Search failed: {response.get_json()}"
    users = response.get_json()
    assert len(users) > 0, f"Search returned empty list: {users}"
    assert users[0]['full_name'] == "Admin Test"

    # 2. Get profile
    response_me = client.get('/api/v1/users/me', headers=admin_headers)
    assert response_me.status_code == 200, f"Failed to get profile: {response_me.get_json()}"
    me = response_me.get_json()
    my_name = me['full_name']
    assert my_name == "Admin Test"

    # 3. Create project with team assignment by name
    project_data = {
        "name": "Team Assign Test",
        "description": "Testing Name Assignment",
        "status": "Active",
        "priority": "Low",
        "startDate": "2026-02-01",
        "deadline": "2026-03-01",
        "team": [
            {"name": my_name}
        ]
    }
    response_create = client.post('/api/v1/projects', json=project_data, headers=admin_headers)
    assert response_create.status_code == 201, f"Project creation failed: {response_create.get_json()}"
    project = response_create.get_json()

    # 4. Verify assignment
    team = project.get('team', [])
    found = any(m['email'] == "admin_test@tt.com" for m in team)
    assert found, f"Project created but user NOT assigned. Team members: {team}"

    # 5. Cleanup
    response_del = client.delete(f'/api/v1/projects/{project["id"]}', headers=admin_headers)
    assert response_del.status_code == 200, f"Failed to delete project: {response_del.get_json()}"
