import pytest
import csv
from io import StringIO
from app.core.database import db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.csat_feedback import CSATFeedback
from app.models.ticket_status_history import TicketStatusHistory
from app.core.constants import UserRole, TicketStatus, TicketPriority
from app.utils.jwt import create_access_token
from tests.test_performance_export import CustomTestConfig

@pytest.fixture
def app():
    from app.main import create_app
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

def test_export_dashboard_report_authorization(client, admin_headers, staff_headers):
    # Test unauthorized (no headers) -> 401
    res = client.get('/api/v1/admin/export-dashboard-report')
    assert res.status_code == 401

    # Test forbidden (IT staff role) -> 403
    res_staff = client.get('/api/v1/admin/export-dashboard-report', headers=staff_headers)
    assert res_staff.status_code == 403

    # Test allowed (Admin role) -> 200
    res_admin = client.get('/api/v1/admin/export-dashboard-report', headers=admin_headers)
    assert res_admin.status_code == 200

def test_export_dashboard_report_formats(app, client, admin_headers):
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

    # Create a ticket resolved by Agent One
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
    res_json = client.get('/api/v1/admin/export-dashboard-report?format=json', headers=admin_headers)
    assert res_json.status_code == 400
    data = res_json.get_json()
    assert "error" in data

    # 2. Test CSV format
    res_csv = client.get('/api/v1/admin/export-dashboard-report?format=csv', headers=admin_headers)
    assert res_csv.status_code == 200
    assert res_csv.headers.get("Content-type") == "text/csv"
    csv_content = res_csv.data.decode('utf-8')
    assert "TICKET-TALLY EXECUTIVE PERFORMANCE REPORT" in csv_content
    assert "SECTION 1: TICKET RESOLUTION TIMES" in csv_content
    assert "SECTION 2: AGENT PERFORMANCE (VOLUME & BREACH RATES)" in csv_content
    assert "SECTION 3: PERFORMANCE METRICS BY CATEGORY" in csv_content
    
    reader = csv.reader(StringIO(csv_content))
    rows = list(reader)
    # Check that some headers exist
    headers_found = [row[0] for row in rows if len(row) > 0]
    assert "EXECUTIVE KPI SUMMARY" in headers_found
    assert "SECTION 1: TICKET RESOLUTION TIMES" in headers_found
    assert "SECTION 2: AGENT PERFORMANCE (VOLUME & BREACH RATES)" in headers_found

    # 3. Test PDF format
    res_pdf = client.get('/api/v1/admin/export-dashboard-report?format=pdf', headers=admin_headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers.get("Content-type") == "application/pdf"
    assert len(res_pdf.data) > 0
    # ReportLab pdf header starts with %PDF
    assert res_pdf.data.startswith(b'%PDF')
