import pytest
from datetime import datetime, timedelta
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.reopen_request import ReopenRequest
from app.core.constants import UserRole, TicketStatus, TicketPriority
from app.utils.jwt import create_access_token
from app.utils.time_utils import utcnow

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
def employee_user(app):
    employee = User(
        email="emp_test@tt.com",
        password_hash="test",
        full_name="Employee Test",
        role=UserRole.EMPLOYEE
    )
    db.session.add(employee)
    db.session.commit()
    return employee

@pytest.fixture
def employee_headers(employee_user):
    token = create_access_token(identity=str(employee_user.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def staff_user(app):
    staff = User(
        email="staff_test@tt.com",
        password_hash="test",
        full_name="Staff Test",
        role=UserRole.IT_STAFF
    )
    db.session.add(staff)
    db.session.commit()
    return staff

@pytest.fixture
def admin_user(app):
    admin = User(
        email="admin_test@tt.com",
        password_hash="test",
        full_name="Admin Test",
        role=UserRole.ADMIN
    )
    db.session.add(admin)
    db.session.commit()
    return admin

@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(identity=str(admin_user.id))
    return {"Authorization": f"Bearer {token}"}

def test_reopen_request_flow(client, employee_user, employee_headers, staff_user, admin_headers):
    # 1. Create a ticket as employee
    ticket = Ticket(
        title="Internet is slow",
        description="Very slow internet speed in room 3",
        category="Network",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        created_by_id=employee_user.id,
        assigned_to_id=staff_user.id
    )
    db.session.add(ticket)
    db.session.commit()

    # 2. Try to request reopen on an Open ticket (should fail)
    response = client.post(
        f'/api/v1/tickets/{ticket.id}/reopen-request',
        json={"reason": "Still slow after fixing"},
        headers=employee_headers
    )
    assert response.status_code == 400
    assert "Cannot request reopen" in response.get_json()["error"]

    # 3. Set ticket status to Resolved
    ticket.status = TicketStatus.RESOLVED
    ticket.updated_at = utcnow()
    db.session.commit()

    # 4. Request reopen with a short reason (should fail)
    response = client.post(
        f'/api/v1/tickets/{ticket.id}/reopen-request',
        json={"reason": "Short reason"},
        headers=employee_headers
    )
    assert response.status_code == 400
    assert "minimum 15 characters" in response.get_json()["error"]

    # 5. Request reopen with a valid reason (should succeed)
    reason_text = "The speed is still under 5Mbps, which does not meet the SLA. Please reopen."
    response = client.post(
        f'/api/v1/tickets/{ticket.id}/reopen-request',
        json={"reason": reason_text},
        headers=employee_headers
    )
    assert response.status_code == 201
    assert response.get_json()["message"] == "Reopen request submitted successfully"

    # 6. Verify duplicate request fails
    response = client.post(
        f'/api/v1/tickets/{ticket.id}/reopen-request',
        json={"reason": "Second request reason that is long enough"},
        headers=employee_headers
    )
    assert response.status_code == 400
    assert "already pending" in response.get_json()["error"]

    # 7. Check ticket detail contains reopen request
    response = client.get(f'/api/v1/tickets/{ticket.id}', headers=employee_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["reopen_request"] is not None
    assert body["reopen_request"]["status"] == "pending"
    assert body["reopen_request"]["reason"] == reason_text

    # 8. Get admin list of reopen requests
    response = client.get('/api/v1/admin/reopen-requests', headers=admin_headers)
    assert response.status_code == 200
    requests_list = response.get_json()
    assert len(requests_list) == 1
    req_id = requests_list[0]["id"]
    assert requests_list[0]["reason"] == reason_text

    # 9. Admin Decline the request (should fail without reason)
    response = client.post(
        f'/api/v1/admin/reopen-requests/{req_id}/decline',
        json={},
        headers=admin_headers
    )
    assert response.status_code == 400, f"Unexpected response: {response.get_json()}"

    # 10. Admin Decline the request (with valid reason)
    decline_reason = "Please create a new ticket, as this is a new bandwidth issue."
    response = client.post(
        f'/api/v1/admin/reopen-requests/{req_id}/decline',
        json={"decline_reason": decline_reason},
        headers=admin_headers
    )
    assert response.status_code == 200, f"Decline failed: {response.get_json()}"

    # 11. Verify ticket is still Resolved and request status is declined
    db.session.refresh(ticket)
    assert ticket.status == TicketStatus.RESOLVED
    
    response = client.get(f'/api/v1/tickets/{ticket.id}', headers=employee_headers)
    body = response.get_json()
    assert body["reopen_request"]["status"] == "declined"
    assert body["reopen_request"]["decline_reason"] == decline_reason

    # 12. Create a new request (should succeed since the previous one was declined)
    response = client.post(
        f'/api/v1/tickets/{ticket.id}/reopen-request',
        json={"reason": "Indeed still slow, please look at it again."},
        headers=employee_headers
    )
    assert response.status_code == 201
    
    response = client.get('/api/v1/admin/reopen-requests', headers=admin_headers)
    requests_list = response.get_json()
    assert len(requests_list) == 1
    new_req_id = requests_list[0]["id"]

    # 13. Admin Approve the reopen request
    response = client.post(
        f'/api/v1/admin/reopen-requests/{new_req_id}/approve',
        headers=admin_headers
    )
    assert response.status_code == 200

    # 14. Verify ticket status is In Progress and assigned back to the staff user
    db.session.refresh(ticket)
    assert ticket.status == TicketStatus.IN_PROGRESS
    assert ticket.assigned_to_id == staff_user.id

def test_reopen_request_expired_limit(client, employee_user, employee_headers):
    # Create ticket resolved 8 days ago
    ticket = Ticket(
        title="Internet is slow",
        description="Very slow speed",
        category="Network",
        status=TicketStatus.RESOLVED,
        priority=TicketPriority.MEDIUM,
        created_by_id=employee_user.id,
        created_at=utcnow() - timedelta(days=8),
        updated_at=utcnow() - timedelta(days=8)
    )
    db.session.add(ticket)
    db.session.commit()

    # Request reopen (should fail because 7 days has passed)
    response = client.post(
        f'/api/v1/tickets/{ticket.id}/reopen-request',
        json={"reason": "Still slow after fixing"},
        headers=employee_headers
    )
    assert response.status_code == 400
    assert "7-day limit has passed" in response.get_json()["error"]
