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
