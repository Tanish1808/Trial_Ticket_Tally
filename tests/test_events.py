import pytest
from datetime import datetime, timedelta
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.event import Event
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
        email="admin_evt@tt.com",
        password_hash="test",
        full_name="Admin Events",
        role=UserRole.ADMIN
    )
    db.session.add(admin)
    db.session.commit()
    token = create_access_token(identity=str(admin.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def employee_headers(app):
    user = User(
        email="emp_evt@tt.com",
        password_hash="test",
        full_name="Employee Events",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}

def test_admin_create_event(client, admin_headers):
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=2)
    payload = {
        "title": "Database Upgrade",
        "description": "Database will be upgraded to PG16.",
        "event_type": "maintenance",
        "start_time": start.isoformat() + "Z",
        "end_time": end.isoformat() + "Z"
    }
    response = client.post('/api/v1/events', json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == "Event created successfully"
    assert data['event']['title'] == "Database Upgrade"
    assert data['event']['event_type'] == "maintenance"

def test_employee_cannot_create_event(client, employee_headers):
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=2)
    payload = {
        "title": "Hacked event",
        "description": "This should fail",
        "event_type": "maintenance",
        "start_time": start.isoformat() + "Z",
        "end_time": end.isoformat() + "Z"
    }
    response = client.post('/api/v1/events', json=payload, headers=employee_headers)
    assert response.status_code == 403

def test_get_events(client, admin_headers, employee_headers):
    # Create an event first
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=2)
    payload = {
        "title": "System Training",
        "description": "Training for staff",
        "event_type": "training",
        "start_time": start.isoformat() + "Z",
        "end_time": end.isoformat() + "Z"
    }
    res = client.post('/api/v1/events', json=payload, headers=admin_headers)
    assert res.status_code == 201

    # Employee gets events
    response = client.get('/api/v1/events', headers=employee_headers)
    assert response.status_code == 200
    events = response.get_json()
    assert len(events) == 1
    assert events[0]['title'] == "System Training"

def test_admin_update_event(client, admin_headers):
    # Create an event
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=2)
    payload = {
        "title": "Event to Update",
        "event_type": "other",
        "start_time": start.isoformat() + "Z",
        "end_time": end.isoformat() + "Z"
    }
    res = client.post('/api/v1/events', json=payload, headers=admin_headers)
    assert res.status_code == 201
    event_id = res.get_json()['event']['id']

    # Update title
    update_payload = {
        "title": "Updated Event Title"
    }
    response = client.patch(f'/api/v1/events/{event_id}', json=update_payload, headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()['event']['title'] == "Updated Event Title"

def test_event_validation_dates(client, admin_headers):
    # Create an event
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=2)
    payload = {
        "title": "Validation Event",
        "event_type": "other",
        "start_time": start.isoformat() + "Z",
        "end_time": end.isoformat() + "Z"
    }
    res = client.post('/api/v1/events', json=payload, headers=admin_headers)
    assert res.status_code == 201
    event_id = res.get_json()['event']['id']

    # Invalid update: end_time <= start_time
    update_payload = {
        "end_time": start.isoformat() + "Z"
    }
    response = client.patch(f'/api/v1/events/{event_id}', json=update_payload, headers=admin_headers)
    assert response.status_code == 400
    assert "error" in response.get_json()

def test_admin_delete_event(client, admin_headers, employee_headers):
    # Create an event
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=2)
    payload = {
        "title": "Event to Delete",
        "event_type": "other",
        "start_time": start.isoformat() + "Z",
        "end_time": end.isoformat() + "Z"
    }
    res = client.post('/api/v1/events', json=payload, headers=admin_headers)
    assert res.status_code == 201
    event_id = res.get_json()['event']['id']

    # Employee cannot delete
    res_emp = client.delete(f'/api/v1/events/{event_id}', headers=employee_headers)
    assert res_emp.status_code == 403

    # Admin deletes
    response = client.delete(f'/api/v1/events/{event_id}', headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()['message'] == "Event deleted successfully"

    # Confirm it's gone
    res_get = client.get('/api/v1/events', headers=admin_headers)
    assert len(res_get.get_json()) == 0
