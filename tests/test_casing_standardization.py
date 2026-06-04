import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.notification import Notification
from app.models.message import Message
from app.models.team import Team
from app.models.team_mapping import TeamMapping
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

def test_auth_responses_casing(client):
    # Test Signup
    signup_data = {
        "email": "signup_test@tt.com",
        "password": "securepassword123",
        "full_name": "Signup Test",
        "role": "employee"
    }
    response = client.post('/api/v1/auth/signup', json=signup_data)
    assert response.status_code == 201
    data = response.get_json()
    assert "accessToken" in data
    assert "access_token" in data
    assert data["accessToken"] == data["access_token"]

    # Test Login
    login_data = {
        "email": "signup_test@tt.com",
        "password": "securepassword123"
    }
    response_login = client.post('/api/v1/auth/login', json=login_data)
    assert response_login.status_code == 200
    data_login = response_login.get_json()
    assert "accessToken" in data_login
    assert "access_token" in data_login
    assert data_login["accessToken"] == data_login["access_token"]

def test_user_responses_casing(client, admin_headers):
    # Test /me response
    response_me = client.get('/api/v1/users/me', headers=admin_headers)
    assert response_me.status_code == 200
    me = response_me.get_json()
    assert "fullName" in me
    assert "teamId" in me
    assert "createdAt" in me
    assert me["fullName"] == "Admin Test"

    # Test /users list response
    response_users = client.get('/api/v1/users', headers=admin_headers)
    assert response_users.status_code == 200
    users = response_users.get_json()
    assert len(users) > 0
    assert "fullName" in users[0]
    assert "ticketsRaised" in users[0]
    assert "ticketsResolved" in users[0]
    assert "isActive" in users[0]
    assert "createdAt" in users[0]

def test_ticket_meta_casing(client, admin_headers):
    response = client.get('/api/v1/tickets', headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    meta = data["meta"]
    assert "perPage" in meta
    assert "totalPages" in meta
    assert "totalItems" in meta

def test_notifications_casing(client, admin_headers, app):
    with app.app_context():
        user = User.query.filter_by(email="admin_test@tt.com").first()
        notif = Notification(user_id=user.id, title="Test", message="Test Notif")
        db.session.add(notif)
        db.session.commit()

    response = client.get('/api/v1/notifications/', headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "unreadCount" in data
    assert len(data["notifications"]) > 0
    n = data["notifications"][0]
    assert "userId" in n
    assert "isRead" in n
    assert "createdAt" in n

def test_admin_analytics_messages_casing(client, admin_headers, app):
    with app.app_context():
        msg = Message(name="Test", email="test@tt.com", subject="Subj", message="Hello")
        db.session.add(msg)
        db.session.commit()

    # Test Analytics
    res_analytics = client.get('/api/v1/admin/analytics', headers=admin_headers)
    assert res_analytics.status_code == 200
    analytics = res_analytics.get_json()
    assert "totalTickets" in analytics
    assert "openTickets" in analytics
    assert "totalUsers" in analytics

    # Test Messages
    res_messages = client.get('/api/v1/admin/messages', headers=admin_headers)
    assert res_messages.status_code == 200
    messages = res_messages.get_json()
    assert len(messages) > 0
    assert "createdAt" in messages[0]
    assert "isRead" in messages[0]

def test_admin_team_mappings_casing(client, admin_headers, app):
    with app.app_context():
        team = Team(name="Test Team")
        db.session.add(team)
        db.session.commit()
        team_id = team.id

    # Test Create Mapping
    create_data = {"category": "Test Cat", "team_id": team_id}
    res_create = client.post('/api/v1/admin/team-mappings', json=create_data, headers=admin_headers)
    assert res_create.status_code == 201
    data = res_create.get_json()
    assert "teamId" in data
    assert "teamName" in data
    mapping_id = data["id"]

    # Test Get Mappings
    res_get = client.get('/api/v1/admin/team-mappings', headers=admin_headers)
    assert res_get.status_code == 200
    mappings = res_get.get_json()
    assert len(mappings) > 0
    assert "teamId" in mappings[0]
    assert "teamName" in mappings[0]

    # Test Update Mapping
    update_data = {"category": "Updated Cat", "team_id": team_id}
    res_update = client.put(f'/api/v1/admin/team-mappings/{mapping_id}', json=update_data, headers=admin_headers)
    assert res_update.status_code == 200
    data_up = res_update.get_json()
    assert "teamId" in data_up
    assert "teamName" in data_up
