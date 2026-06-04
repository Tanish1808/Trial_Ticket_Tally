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

def test_restriction(client, admin_headers):
    # 1. Create Project
    project_data = {
        "name": "Test Restriction Project",
        "description": "Testing locked status",
        "status": "Active",
        "priority": "Low",
        "startDate": "2026-01-01",
        "deadline": "2026-12-31"
    }
    response = client.post('/api/v1/projects', json=project_data, headers=admin_headers)
    assert response.status_code == 201, f"Failed to create project: {response.get_json()}"
    body = response.get_json()
    project_id = body['id']

    # 2. Mark as Completed
    response = client.patch(f'/api/v1/projects/{project_id}', json={"status": "Completed"}, headers=admin_headers)
    assert response.status_code == 200, f"Failed to mark completed: {response.get_json()}"

    # 3. Attempt Edit (should fail with 400 Bad Request)
    response = client.patch(f'/api/v1/projects/{project_id}', json={"description": "Hacked"}, headers=admin_headers)
    assert response.status_code == 400, f"FAILURE: Edit allowed! Status: {response.status_code}, Response: {response.get_json()}"
    
    # 4. Cleanup (Soft Delete)
    response = client.delete(f'/api/v1/projects/{project_id}', headers=admin_headers)
    assert response.status_code == 200, f"Failed to delete project: {response.get_json()}"

    # 5. Verify Soft Delete (should return 404 Not Found since it is soft-deleted)
    response_get = client.get(f'/api/v1/projects/{project_id}', headers=admin_headers)
    assert response_get.status_code == 404, f"Project was not soft deleted (still queryable): {response_get.get_json()}"
