import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.core.constants import UserRole, TicketStatus, TicketPriority, SLAStatus
from app.models.ticket import Ticket
from app.models.ticket_status_history import TicketStatusHistory
from app.services.sla_service import SLAService
from datetime import datetime, timedelta
from app.utils.time_utils import utcnow
from app.utils.password import hash_password

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
def auth_headers(client, app):
    # Setup test users
    with app.app_context():
        # Clean users if any
        db.session.query(User).delete()
        db.session.commit()
        
        admin = User(
            email="admin@test.com",
            password_hash=hash_password("adminpass"),
            full_name="Admin User",
            role=UserRole.ADMIN
        )
        
        employee = User(
            email="emp@test.com",
            password_hash=hash_password("emppass"),
            full_name="Emp User",
            role=UserRole.EMPLOYEE
        )
        
        db.session.add(admin)
        db.session.add(employee)
        db.session.commit()
        
        admin_id = admin.id
        employee_id = employee.id

    # Admin Login
    response = client.post('/api/v1/auth/login', json={
        "email": "admin@test.com",
        "password": "adminpass"
    })
    admin_token = response.json['access_token']
    
    # Employee Login
    response = client.post('/api/v1/auth/login', json={
        "email": "emp@test.com",
        "password": "emppass"
    })
    emp_token = response.json['access_token']
    
    return {
        "admin": {"Authorization": f"Bearer {admin_token}"},
        "employee": {"Authorization": f"Bearer {emp_token}"},
        "admin_id": admin_id,
        "employee_id": employee_id
    }

def test_link_github_pr_api(client, app, auth_headers):
    # Create ticket
    response = client.post('/api/v1/tickets', json={
        "title": "Fix VPN",
        "description": "VPN issues",
        "category": "Network Issue",
        "priority": "High"
    }, headers=auth_headers['employee'])
    assert response.status_code == 201
    
    # Get all tickets to find the ID
    response = client.get('/api/v1/tickets', headers=auth_headers['admin'])
    ticket_id = response.json['items'][0]['id']
    
    # Verify initially no PR
    response = client.get(f'/api/v1/tickets/{ticket_id}', headers=auth_headers['admin'])
    assert response.json['github_pr_url'] is None
    
    # Link PR URL
    pr_url = "https://github.com/test-org/test-repo/pull/123"
    response = client.patch(f'/api/v1/tickets/{ticket_id}', json={
        "github_pr_url": pr_url
    }, headers=auth_headers['admin'])
    assert response.status_code == 200
    
    # Verify linked PR URL is returned
    response = client.get(f'/api/v1/tickets/{ticket_id}', headers=auth_headers['admin'])
    assert response.json['github_pr_url'] == pr_url
    
    # Unlink PR URL (pass empty string)
    response = client.patch(f'/api/v1/tickets/{ticket_id}', json={
        "github_pr_url": ""
    }, headers=auth_headers['admin'])
    assert response.status_code == 200
    
    # Verify unlinked
    response = client.get(f'/api/v1/tickets/{ticket_id}', headers=auth_headers['admin'])
    assert response.json['github_pr_url'] is None

def test_github_webhook_merge_resolves_ticket(client, app, auth_headers):
    # Create ticket
    response = client.post('/api/v1/tickets', json={
        "title": "Database Fix",
        "description": "Query optimization",
        "category": "Software Issue",
        "priority": "High"
    }, headers=auth_headers['employee'])
    
    response = client.get('/api/v1/tickets', headers=auth_headers['admin'])
    ticket_id = response.json['items'][0]['id']
    
    # Link PR
    pr_url = "https://github.com/test-org/test-repo/pull/456"
    client.patch(f'/api/v1/tickets/{ticket_id}', json={
        "github_pr_url": pr_url
    }, headers=auth_headers['admin'])
    
    # Verify status is OPEN (or default first status, e.g. Open)
    response = client.get(f'/api/v1/tickets/{ticket_id}', headers=auth_headers['admin'])
    assert response.json['status'] == "Open"
    
    # Send mock webhook payload (merged: True)
    # Target date: 1 hour after creation (within SLA, High SLA is 8 hours)
    with app.app_context():
        ticket = Ticket.query.get(ticket_id)
        created_at = ticket.created_at
        
    merge_time = created_at + timedelta(hours=1)
    merge_time_str = merge_time.isoformat() + "Z"
    
    webhook_payload = {
        "action": "closed",
        "pull_request": {
            "html_url": pr_url,
            "merged": True,
            "merged_at": merge_time_str
        }
    }
    
    response = client.post('/api/v1/github/webhook', 
                           json=webhook_payload, 
                           headers={"X-GitHub-Event": "pull_request"})
    assert response.status_code == 200
    assert response.json['status'] == "success"
    
    # Verify ticket status is now RESOLVED
    response = client.get(f'/api/v1/tickets/{ticket_id}', headers=auth_headers['admin'])
    assert response.json['status'] == "Resolved"
    
    # Verify SLA status evaluates to ACHIEVED
    with app.app_context():
        ticket_db = Ticket.query.get(ticket_id)
        assert SLAService.check_sla_status(ticket_db) == SLAStatus.ACHIEVED

def test_github_webhook_merge_sla_breach(client, app, auth_headers):
    # Create ticket
    response = client.post('/api/v1/tickets', json={
        "title": "Critical Patch",
        "description": "Security vulnerability",
        "category": "Software Issue",
        "priority": "Critical"
    }, headers=auth_headers['employee'])
    
    response = client.get('/api/v1/tickets', headers=auth_headers['admin'])
    ticket_id = response.json['items'][0]['id']
    
    # Link PR
    pr_url = "https://github.com/test-org/test-repo/pull/789"
    client.patch(f'/api/v1/tickets/{ticket_id}', json={
        "github_pr_url": pr_url
    }, headers=auth_headers['admin'])
    
    # Webhook merge time: 5 hours after creation (exceeds Critical SLA of 4 hours)
    with app.app_context():
        ticket = Ticket.query.get(ticket_id)
        created_at = ticket.created_at
        
    merge_time = created_at + timedelta(hours=5)
    merge_time_str = merge_time.isoformat() + "Z"
    
    webhook_payload = {
        "action": "closed",
        "pull_request": {
            "html_url": pr_url,
            "merged": True,
            "merged_at": merge_time_str
        }
    }
    
    response = client.post('/api/v1/github/webhook', 
                           json=webhook_payload, 
                           headers={"X-GitHub-Event": "pull_request"})
    assert response.status_code == 200
    
    # Verify ticket status is RESOLVED
    response = client.get(f'/api/v1/tickets/{ticket_id}', headers=auth_headers['admin'])
    assert response.json['status'] == "Resolved"
    
    # Verify SLA status evaluates to BREACHED because it took 5 hours
    with app.app_context():
        ticket_db = Ticket.query.get(ticket_id)
        assert SLAService.check_sla_status(ticket_db) == SLAStatus.BREACHED
