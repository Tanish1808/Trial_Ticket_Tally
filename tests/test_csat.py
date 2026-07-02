import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.csat_feedback import CSATFeedback
from app.core.constants import UserRole, TicketStatus, TicketPriority
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
def auth_headers(app):
    # Setup test users
    employee1 = User(
        email="emp1@tt.com",
        password_hash="test",
        full_name="Employee One",
        role=UserRole.EMPLOYEE
    )
    employee2 = User(
        email="emp2@tt.com",
        password_hash="test",
        full_name="Employee Two",
        role=UserRole.EMPLOYEE
    )
    admin = User(
        email="admin@tt.com",
        password_hash="test",
        full_name="Admin User",
        role=UserRole.ADMIN
    )
    db.session.add_all([employee1, employee2, admin])
    db.session.commit()

    token1 = create_access_token(identity=str(employee1.id))
    token2 = create_access_token(identity=str(employee2.id))
    admin_token = create_access_token(identity=str(admin.id))

    return {
        "employee1": {"Authorization": f"Bearer {token1}"},
        "employee2": {"Authorization": f"Bearer {token2}"},
        "admin": {"Authorization": f"Bearer {admin_token}"},
        "employee1_id": employee1.id,
        "employee2_id": employee2.id,
        "admin_id": admin.id
    }

def test_csat_feedback_creation_unauthorized(client, auth_headers):
    # Create an Open ticket by employee1
    t = Ticket(
        title="VPN issue",
        description="Help",
        category="Network Issue",
        priority=TicketPriority.LOW,
        created_by_id=auth_headers["employee1_id"],
        status=TicketStatus.RESOLVED
    )
    db.session.add(t)
    db.session.commit()

    # Employee 2 attempts to rate Employee 1's ticket -> should fail with 403
    response = client.post(f'/api/v1/tickets/{t.id}/feedback', json={
        "rating": 5,
        "comment": "Nice support!"
    }, headers=auth_headers["employee2"])

    assert response.status_code == 403
    assert "Only the ticket creator can submit feedback" in response.get_json()["error"]

def test_csat_feedback_creation_invalid_status(client, auth_headers):
    # Create an Open ticket by employee1 (not resolved/closed)
    t = Ticket(
        title="VPN issue",
        description="Help",
        category="Network Issue",
        priority=TicketPriority.LOW,
        created_by_id=auth_headers["employee1_id"],
        status=TicketStatus.OPEN
    )
    db.session.add(t)
    db.session.commit()

    # Employee 1 attempts to rate Open ticket -> should fail with 400
    response = client.post(f'/api/v1/tickets/{t.id}/feedback', json={
        "rating": 5
    }, headers=auth_headers["employee1"])

    assert response.status_code == 400
    assert "Feedback can only be submitted for Resolved or Closed tickets" in response.get_json()["error"]

def test_csat_feedback_creation_success(client, auth_headers):
    # Create a Resolved ticket by employee1
    t = Ticket(
        title="VPN issue",
        description="Help",
        category="Network Issue",
        priority=TicketPriority.LOW,
        created_by_id=auth_headers["employee1_id"],
        status=TicketStatus.RESOLVED
    )
    db.session.add(t)
    db.session.commit()

    # Employee 1 submits feedback -> should succeed with 201
    response = client.post(f'/api/v1/tickets/{t.id}/feedback', json={
        "rating": 5,
        "comment": "Excellent support, resolved quickly!"
    }, headers=auth_headers["employee1"])

    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "Feedback submitted successfully"
    assert data["feedback"]["rating"] == 5
    assert data["feedback"]["comment"] == "Excellent support, resolved quickly!"

    # Verify feedback details are returned when fetching the ticket
    res_get = client.get(f'/api/v1/tickets/{t.id}', headers=auth_headers["employee1"])
    assert res_get.status_code == 200
    ticket_data = res_get.get_json()
    assert ticket_data["feedback"] is not None
    assert ticket_data["feedback"]["rating"] == 5
    assert ticket_data["feedback"]["comment"] == "Excellent support, resolved quickly!"

def test_csat_feedback_creation_duplicate(client, auth_headers):
    # Create a Resolved ticket by employee1
    t = Ticket(
        title="VPN issue",
        description="Help",
        category="Network Issue",
        priority=TicketPriority.LOW,
        created_by_id=auth_headers["employee1_id"],
        status=TicketStatus.RESOLVED
    )
    db.session.add(t)
    db.session.commit()

    # First submission -> 201
    response1 = client.post(f'/api/v1/tickets/{t.id}/feedback', json={"rating": 4}, headers=auth_headers["employee1"])
    assert response1.status_code == 201

    # Second submission -> 409 Conflict
    response2 = client.post(f'/api/v1/tickets/{t.id}/feedback', json={"rating": 3}, headers=auth_headers["employee1"])
    assert response2.status_code == 409
    assert "Feedback has already been submitted for this ticket" in response2.get_json()["error"]

def test_dashboard_csat_analytics(client, auth_headers):
    # Create resolved tickets
    t1 = Ticket(
        title="T1", description="H", category="Network Issue",
        priority=TicketPriority.LOW, created_by_id=auth_headers["employee1_id"],
        status=TicketStatus.RESOLVED, is_demo=False
    )
    t2 = Ticket(
        title="T2", description="H", category="Software Issue",
        priority=TicketPriority.LOW, created_by_id=auth_headers["employee2_id"],
        status=TicketStatus.RESOLVED, is_demo=False
    )
    t_demo = Ticket(
        title="T Demo", description="H", category="Software Issue",
        priority=TicketPriority.LOW, created_by_id=auth_headers["employee2_id"],
        status=TicketStatus.RESOLVED, is_demo=True # DEMO should be excluded from stats
    )
    db.session.add_all([t1, t2, t_demo])
    db.session.commit()

    # Add CSAT feedbacks
    fb1 = CSATFeedback(rating=5, comment="Great", ticket_id=t1.id, user_id=auth_headers["employee1_id"])
    fb2 = CSATFeedback(rating=3, comment="Ok", ticket_id=t2.id, user_id=auth_headers["employee2_id"])
    fb_demo = CSATFeedback(rating=1, comment="Bad", ticket_id=t_demo.id, user_id=auth_headers["employee2_id"])
    db.session.add_all([fb1, fb2, fb_demo])
    db.session.commit()

    # Get admin dashboard analytics
    response = client.get('/api/v1/analytics/dashboard', headers=auth_headers["admin"])
    assert response.status_code == 200
    data = response.get_json()

    # Total and Average should exclude demo: (5 + 3) / 2 = 4.0 average
    assert data["csat"] is not None
    assert data["csat"]["total"] == 2
    assert data["csat"]["average"] == 4.0
    assert data["csat"]["breakdown"]["5"] == 1
    assert data["csat"]["breakdown"]["3"] == 1
    assert data["csat"]["breakdown"]["1"] == 0 # Excluded demo rating
    assert len(data["csat"]["recent"]) == 2
    assert data["csat"]["recent"][0]["ticketTitle"] in ["T1", "T2"]
