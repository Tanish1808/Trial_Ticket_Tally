import pytest
import csv
import json
from io import StringIO
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.csat_feedback import CSATFeedback
from app.models.ticket_status_history import TicketStatusHistory
from app.core.constants import UserRole, TicketStatus, TicketPriority
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
def admin_headers(app):
    user = User(
        email="admin_user@tt.com",
        password_hash="test",
        full_name="Admin User",
        role=UserRole.ADMIN
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def staff_headers(app):
    user = User(
        email="staff_user@tt.com",
        password_hash="test",
        full_name="Staff User",
        role=UserRole.IT_STAFF
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}

def test_export_performance_authorization(client, admin_headers, staff_headers):
    # Test unauthorized (no headers) -> 401
    res = client.get('/api/v1/admin/export-performance')
    assert res.status_code == 401

    # Test forbidden (IT staff role) -> 403
    res_staff = client.get('/api/v1/admin/export-performance', headers=staff_headers)
    assert res_staff.status_code == 403

    # Test allowed (Admin role) -> 200
    res_admin = client.get('/api/v1/admin/export-performance', headers=admin_headers)
    assert res_admin.status_code == 200

def test_export_performance_formats(app, client, admin_headers):
    # Create IT staff member
    staff = User(
        email="agent@tt.com",
        password_hash="test",
        full_name="Agent One",
        role=UserRole.IT_STAFF
    )
    # Create employee user to be the creator
    employee = User(
        email="emp@tt.com",
        password_hash="test",
        full_name="Employee One",
        role=UserRole.EMPLOYEE
    )
    db.session.add_all([staff, employee])
    db.session.commit()

    # Create a ticket resolved by Agent One with CSAT feedback
    t_resolved = Ticket(
        title="Resolved Ticket",
        description="Ticket description",
        category="Software",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.RESOLVED,
        created_by_id=employee.id,
        assigned_to_id=staff.id,
        is_demo=False
    )
    db.session.add(t_resolved)
    db.session.commit()

    # Add SLA history for the ticket so SLA calculation works (resolved_at <= deadline => Achieved)
    h = TicketStatusHistory(
        ticket_id=t_resolved.id,
        old_status=TicketStatus.IN_PROGRESS,
        new_status=TicketStatus.RESOLVED,
        changed_by_id=staff.id,
        changed_at=t_resolved.created_at
    )
    db.session.add(h)

    # Add CSAT Feedback
    feedback = CSATFeedback(
        rating=5,
        comment="Great job!",
        ticket_id=t_resolved.id,
        user_id=employee.id
    )
    db.session.add(feedback)
    db.session.commit()

    # 1. Test JSON format (should return 400 since JSON is disallowed)
    res_json = client.get('/api/v1/admin/export-performance?format=json', headers=admin_headers)
    assert res_json.status_code == 400
    data = res_json.get_json()
    assert "error" in data

    # 2. Test CSV format
    res_csv = client.get('/api/v1/admin/export-performance?format=csv', headers=admin_headers)
    assert res_csv.status_code == 200
    assert res_csv.headers.get("Content-type") == "text/csv"
    csv_content = res_csv.data.decode('utf-8')
    reader = csv.reader(StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 2 # Header + 1 staff row
    assert rows[0] == ['Name', 'Email', 'Team', 'Active Tickets', 'Resolved Tickets', 'Avg CSAT', 'SLA Compliance']
    assert rows[1][0] == "Agent One"
    assert rows[1][4] == "1" # Resolved
    assert rows[1][5] == "5.0" # CSAT
    assert rows[1][6] == "100.0%" # SLA

    # 3. Test PDF format
    res_pdf = client.get('/api/v1/admin/export-performance?format=pdf', headers=admin_headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers.get("Content-type") == "application/pdf"
    assert len(res_pdf.data) > 0
