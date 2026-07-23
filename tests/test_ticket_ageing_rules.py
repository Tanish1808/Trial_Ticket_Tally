import pytest
from datetime import datetime, timedelta
from app.utils.time_utils import utcnow
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.core.constants import UserRole, TicketStatus
from app.services.ticket_service import TicketService
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
def test_user(app):
    user = User(
        email="user_test@tt.com",
        password_hash="test",
        full_name="User Test",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def staff_user(app):
    user = User(
        email="staff_test@tt.com",
        password_hash="test",
        full_name="Staff Test",
        role=UserRole.IT_STAFF
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def staff_headers(app, staff_user):
    token = create_access_token(identity=str(staff_user.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def user_headers(app, test_user):
    token = create_access_token(identity=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}

def test_prevent_manual_status_to_closed(app, client, staff_headers, test_user):
    with app.app_context():
        ticket = Ticket(
            title="Test Ticket",
            description="Testing manual close blocking",
            category="Software Issue",
            status=TicketStatus.OPEN,
            created_by_id=test_user.id
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    # Try updating the ticket status to CLOSED via API
    response = client.put(
        f'/api/v1/tickets/{ticket_id}',
        json={"status": "Closed"},
        headers=staff_headers
    )
    assert response.status_code in [400, 404]
    res_data = response.get_json()
    assert "Manual status transition to Closed is not allowed" in res_data["error"]

    with app.app_context():
        t = db.session.get(Ticket, ticket_id)
        assert t.status == TicketStatus.OPEN

def test_prevent_updating_closed_ticket(app, client, staff_headers, test_user):
    with app.app_context():
        ticket = Ticket(
            title="Closed Ticket",
            description="Testing update blocking",
            category="Software Issue",
            status=TicketStatus.CLOSED,
            created_by_id=test_user.id
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    # Try changing priority via API
    response = client.put(
        f'/api/v1/tickets/{ticket_id}',
        json={"priority": "High"},
        headers=staff_headers
    )
    assert response.status_code in [400, 404]
    res_data = response.get_json()
    assert "Cannot update a closed ticket" in res_data["error"]

def test_prevent_commenting_on_closed_ticket(app, client, user_headers, test_user):
    with app.app_context():
        ticket = Ticket(
            title="Closed Ticket",
            description="Testing comment blocking",
            category="Software Issue",
            status=TicketStatus.CLOSED,
            created_by_id=test_user.id
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    # Try posting a comment via API
    response = client.post(
        f'/api/v1/tickets/{ticket_id}/comments',
        json={"text": "Adding a comment to a closed ticket should fail"},
        headers=user_headers
    )
    assert response.status_code == 400
    res_data = response.get_json()
    assert "Cannot add comments to a closed ticket" in res_data["error"]

def test_ticket_ageing_scheduler(app, test_user):
    with app.app_context():
        now = utcnow()
        
        # Ticket 1: Resolved 8 days ago (should age to Close)
        t1 = Ticket(
            title="Old Resolved Ticket",
            description="Resolved 8 days ago",
            category="Software Issue",
            status=TicketStatus.RESOLVED,
            created_by_id=test_user.id
        )
        db.session.add(t1)
        
        # Ticket 2: Resolved 2 days ago (should remain Resolved)
        t2 = Ticket(
            title="New Resolved Ticket",
            description="Resolved 2 days ago",
            category="Software Issue",
            status=TicketStatus.RESOLVED,
            created_by_id=test_user.id
        )
        db.session.add(t2)
        
        # Ticket 3: Open 10 days ago (should remain Open)
        t3 = Ticket(
            title="Old Open Ticket",
            description="Open 10 days ago",
            category="Software Issue",
            status=TicketStatus.OPEN,
            created_by_id=test_user.id
        )
        db.session.add(t3)
        
        db.session.commit()
        
        # Artificially set updated_at back
        t1.updated_at = now - timedelta(days=8)
        t2.updated_at = now - timedelta(days=2)
        t3.updated_at = now - timedelta(days=10)
        db.session.commit()
        
        t1_id = t1.id
        t2_id = t2.id
        t3_id = t3.id

        # Run auto_close_resolved_tickets
        TicketService.auto_close_resolved_tickets()
        
        # Retrieve tickets from DB
        db.session.expire_all()
        t1_db = db.session.get(Ticket, t1_id)
        t2_db = db.session.get(Ticket, t2_id)
        t3_db = db.session.get(Ticket, t3_id)
        
        assert t1_db.status == TicketStatus.CLOSED
        assert t2_db.status == TicketStatus.RESOLVED
        assert t3_db.status == TicketStatus.OPEN
