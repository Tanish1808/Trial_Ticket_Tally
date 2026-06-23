import pytest
from datetime import datetime, timedelta
from app.utils.time_utils import utcnow
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.announcement import Announcement
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
        email="admin_ann@tt.com",
        password_hash="test",
        full_name="Admin Announcements",
        role=UserRole.ADMIN
    )
    db.session.add(admin)
    db.session.commit()
    token = create_access_token(identity=str(admin.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def employee_headers(app):
    user = User(
        email="emp_ann@tt.com",
        password_hash="test",
        full_name="Employee Announcements",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}

def test_admin_create_announcement(client, admin_headers):
    payload = {
        "title": "Scheduled Maintenance",
        "message": "System will be down for 2 hours on Sunday."
    }
    response = client.post('/api/v1/admin/announcements', json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == "Announcement created"
    assert data['announcement']['title'] == "Scheduled Maintenance"
    assert data['announcement']['created_by'] == "Admin Announcements"

def test_employee_cannot_create_announcement(client, employee_headers):
    payload = {
        "title": "Hacked",
        "message": "Should fail"
    }
    response = client.post('/api/v1/admin/announcements', json=payload, headers=employee_headers)
    assert response.status_code == 403

def test_get_active_announcements(client, admin_headers, employee_headers):
    # Post active announcement
    payload_active = {
        "title": "Active Announce",
        "message": "This is visible"
    }
    res1 = client.post('/api/v1/admin/announcements', json=payload_active, headers=admin_headers)
    assert res1.status_code == 201

    # Post expired announcement
    payload_expired = {
        "title": "Expired Announce",
        "message": "This is hidden",
        "expires_at": (utcnow() - timedelta(hours=1)).isoformat()
    }
    res2 = client.post('/api/v1/admin/announcements', json=payload_expired, headers=admin_headers)
    assert res2.status_code == 201

    # Call public endpoint
    response = client.get('/api/v1/announcements', headers=employee_headers)
    assert response.status_code == 200
    announcements = response.get_json()
    
    # Assert only the active one is returned
    assert len(announcements) == 1
    assert announcements[0]['title'] == "Active Announce"

def test_admin_delete_announcement(client, admin_headers, employee_headers):
    # Post active announcement
    payload = {
        "title": "Temp Announce",
        "message": "Will delete"
    }
    res_create = client.post('/api/v1/admin/announcements', json=payload, headers=admin_headers)
    assert res_create.status_code == 201
    created_id = res_create.get_json()['announcement']['id']

    # Delete it
    res_delete = client.delete(f'/api/v1/admin/announcements/{created_id}', headers=admin_headers)
    assert res_delete.status_code == 200
    assert res_delete.get_json()['message'] == "Announcement deleted"

    # Verify public feed is empty
    res_feed = client.get('/api/v1/announcements', headers=employee_headers)
    assert len(res_feed.get_json()) == 0
