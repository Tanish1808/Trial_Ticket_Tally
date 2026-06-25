import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.core.constants import UserRole, TicketStatus, TicketPriority
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.ticket_status_history import TicketStatusHistory
from app.utils.jwt import create_access_token

class CustomTestConfig(TestingConfig):
    CORS_ALLOWED_ORIGINS = "http://allowed.com"

@pytest.fixture
def app():
    app = create_app(CustomTestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(app):
    user = User(
        email="test_user@tt.com",
        password_hash="test",
        full_name="Test User",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}

def test_cors_headers(client):
    # Test allowed origin
    headers = {"Origin": "http://allowed.com"}
    response = client.get('/api/v1/tickets', headers=headers)
    assert response.headers.get("Access-Control-Allow-Origin") == "http://allowed.com"

    # Test disallowed origin
    headers_disallowed = {"Origin": "http://disallowed.com"}
    response_disallowed = client.get('/api/v1/tickets', headers=headers_disallowed)
    assert response_disallowed.headers.get("Access-Control-Allow-Origin") != "http://disallowed.com"

def test_pagination_limit(client, auth_headers):
    # Add a couple of tickets
    user = User.query.filter_by(email="test_user@tt.com").first()
    for i in range(15):
        t = Ticket(
            title=f"Ticket {i}",
            description="Desc",
            category="Software Issue",
            priority=TicketPriority.LOW,
            created_by_id=user.id
        )
        db.session.add(t)
    db.session.commit()

    # Request with per_page=5
    response = client.get('/api/v1/tickets?per_page=5', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['items']) == 5
    assert data['meta']['per_page'] == 5

    # Request with per_page=150 (should be capped at 100)
    response_capped = client.get('/api/v1/tickets?per_page=150', headers=auth_headers)
    assert response_capped.status_code == 200
    data_capped = response_capped.get_json()
    assert data_capped['meta']['per_page'] == 100

def test_get_ticket_by_id_eager_loading(app, auth_headers):
    # Create ticket, comments, and history
    user = User.query.filter_by(email="test_user@tt.com").first()
    t = Ticket(
        title="Test Ticket",
        description="Desc",
        category="Software Issue",
        priority=TicketPriority.LOW,
        created_by_id=user.id
    )
    db.session.add(t)
    db.session.commit()

    c1 = Comment(text="Comment 1", ticket_id=t.id, user_id=user.id)
    c2 = Comment(text="Comment 2", ticket_id=t.id, user_id=user.id)
    h1 = TicketStatusHistory(ticket_id=t.id, old_status=None, new_status=TicketStatus.OPEN, changed_by_id=user.id)
    db.session.add_all([c1, c2, h1])
    db.session.commit()

    # Clear session to force reloading from DB
    db.session.expire_all()

    from app.services.ticket_service import TicketService
    # Fetch ticket
    fetched = TicketService.get_ticket_by_id(t.id)
    assert fetched is not None
    assert fetched.title == "Test Ticket"
    
    # Verify relations are loaded/accessible
    assert len(fetched.comments) == 2
    assert fetched.comments[0].author.full_name == "Test User"
    assert len(fetched.status_history) == 1
    assert fetched.status_history[0].changed_by.full_name == "Test User"

def test_pdf_download_authorization(app, client, auth_headers):
    employee_user = User.query.filter_by(email="test_user@tt.com").first()
    
    admin_user = User(
        email="admin_user@tt.com",
        password_hash="test",
        full_name="Admin User",
        role=UserRole.ADMIN
    )
    it_user = User(
        email="it_user@tt.com",
        password_hash="test",
        full_name="IT User",
        role=UserRole.IT_STAFF
    )
    other_employee = User(
        email="other_employee@tt.com",
        password_hash="test",
        full_name="Other Employee",
        role=UserRole.EMPLOYEE
    )
    db.session.add_all([admin_user, it_user, other_employee])
    db.session.commit()
    
    admin_token = create_access_token(identity=str(admin_user.id))
    it_token = create_access_token(identity=str(it_user.id))
    other_token = create_access_token(identity=str(other_employee.id))
    
    t = Ticket(
        title="PDF Auth Test Ticket",
        description="Desc",
        category="Software Issue",
        priority=TicketPriority.LOW,
        created_by_id=employee_user.id,
        assigned_to_id=it_user.id
    )
    db.session.add(t)
    db.session.commit()
    
    # Test creator (employee_user) can download (should be 200)
    res_creator = client.get(f'/api/v1/tickets/{t.id}/pdf', headers=auth_headers)
    assert res_creator.status_code == 200
    
    # Test assignee (it_user) can download (should be 200)
    res_assignee = client.get(f'/api/v1/tickets/{t.id}/pdf', headers={"Authorization": f"Bearer {it_token}"})
    assert res_assignee.status_code == 200
    
    # Test admin can download (should be 200)
    res_admin = client.get(f'/api/v1/tickets/{t.id}/pdf', headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    
    # Test unauthorized user (other_employee) cannot download (should be 403)
    res_unauth = client.get(f'/api/v1/tickets/{t.id}/pdf', headers={"Authorization": f"Bearer {other_token}"})
    assert res_unauth.status_code == 403

def test_json_logging(monkeypatch, capsys):
    import json
    import logging
    
    # Set JSON_LOGGING environment variable to force JSON formatted logs
    monkeypatch.setenv("JSON_LOGGING", "True")
    
    # Import create_app and initialize with TestingConfig to configure logging
    from app.main import create_app
    app = create_app(CustomTestConfig)
    
    # Log a message
    logger = logging.getLogger("test_json_logger")
    logger.info("Test JSON Log Message")
    
    # Read captured stdout and stderr outputs
    captured = capsys.readouterr()
    log_lines = captured.err.splitlines() + captured.out.splitlines()
    
    json_log = None
    for line in log_lines:
        if "Test JSON Log Message" in line:
            json_log = json.loads(line.strip())
            break
            
    assert json_log is not None, f"Could not find JSON log in output lines: {log_lines}"
    assert json_log["level"] == "INFO"
    assert json_log["message"] == "Test JSON Log Message"

def test_broadcast_live_activity_demo_status(app, auth_headers, monkeypatch):
    from app.services.notification_service import NotificationService
    from app.models.ticket import Ticket
    from app.core.constants import TicketPriority
    
    # Mock socketio.emit
    emitted_data = []
    def mock_emit(event, data):
        if event == 'live_activity':
            emitted_data.append(data)
            
    from app.main import socketio
    monkeypatch.setattr(socketio, 'emit', mock_emit)
    
    user = User.query.first()
    
    # 1. Create a non-demo ticket
    t_normal = Ticket(
        title="Normal Ticket",
        description="Normal Desc",
        category="Software Issue",
        priority=TicketPriority.LOW,
        created_by_id=user.id,
        is_demo=False
    )
    db.session.add(t_normal)
    db.session.commit()
    
    # Broadcast for normal ticket
    NotificationService.broadcast_live_activity(
        category="created",
        ticket_id=t_normal.id,
        message="Normal ticket created",
        created_by="Test User"
    )
    assert len(emitted_data) == 1
    assert emitted_data[0]['is_demo'] is False
    
    # 2. Create a demo ticket
    t_demo = Ticket(
        title="Demo Ticket",
        description="Demo Desc",
        category="Software Issue",
        priority=TicketPriority.LOW,
        created_by_id=user.id,
        is_demo=True
    )
    db.session.add(t_demo)
    db.session.commit()
    
    # Broadcast for demo ticket
    NotificationService.broadcast_live_activity(
        category="created",
        ticket_id=t_demo.id,
        message="Demo ticket created",
        created_by="Test User"
    )
    assert len(emitted_data) == 2
    assert emitted_data[1]['is_demo'] is True



