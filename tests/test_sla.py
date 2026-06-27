import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.core.constants import UserRole, TicketStatus, TicketPriority, SLAStatus
from app.models.ticket import Ticket
from app.models.sla import SLA
from app.models.ticket_status_history import TicketStatusHistory
from app.services.sla_service import SLAService
from datetime import datetime, timedelta
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

def test_sla_seeding(app):
    # SLA table is initially empty in the test DB
    assert SLA.query.count() == 0
    
    # Run seeder
    SLAService.seed_default_slas()
    
    # Check seeded values
    slas = SLA.query.all()
    assert len(slas) == 4
    
    critical_sla = SLA.query.filter_by(priority=TicketPriority.CRITICAL).first()
    assert critical_sla is not None
    assert critical_sla.resolution_time_hours == 4
    
    low_sla = SLA.query.filter_by(priority=TicketPriority.LOW).first()
    assert low_sla is not None
    assert low_sla.resolution_time_hours == 48

def test_sla_deadline_fallback_and_db(app):
    user = User(
        email="employee_test@tt.com",
        password_hash="test",
        full_name="Employee",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    
    ticket = Ticket(
        title="Test Ticket",
        description="Low priority ticket",
        category="General",
        priority=TicketPriority.LOW,
        created_by_id=user.id
    )
    db.session.add(ticket)
    db.session.commit()
    
    # Test deadline calculation with fallback (when SLA table is empty)
    deadline = SLAService.get_deadline(ticket)
    expected_deadline = ticket.created_at + timedelta(hours=48)
    assert abs((deadline - expected_deadline).total_seconds()) < 1.0

    # Modify SLA in DB and check if it updates dynamically
    low_sla = SLA.query.filter_by(priority=TicketPriority.LOW).first()
    low_sla.resolution_time_hours = 12
    db.session.commit()
    
    new_deadline = SLAService.get_deadline(ticket)
    expected_new_deadline = ticket.created_at + timedelta(hours=12)
    assert abs((new_deadline - expected_new_deadline).total_seconds()) < 1.0

def test_check_sla_status_active_pending(app):
    user = User(
        email="employee_test@tt.com",
        password_hash="test",
        full_name="Employee",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    
    ticket = Ticket(
        title="Test Ticket",
        description="Med priority ticket",
        category="General",
        priority=TicketPriority.MEDIUM,
        created_by_id=user.id,
        created_at=utcnow() - timedelta(hours=2) # 2 hours old, Medium is 24 hours
    )
    db.session.add(ticket)
    db.session.commit()
    
    status = SLAService.check_sla_status(ticket)
    assert status == SLAStatus.PENDING

def test_check_sla_status_active_approaching(app):
    user = User(
        email="employee_test@tt.com",
        password_hash="test",
        full_name="Employee",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    
    # SLA for Critical is 4 hours. 80% is 3.2 hours. Let's make it 3.5 hours old.
    ticket = Ticket(
        title="Test Ticket",
        description="Critical ticket",
        category="General",
        priority=TicketPriority.CRITICAL,
        created_by_id=user.id,
        created_at=utcnow() - timedelta(minutes=210) # 3.5 hours old
    )
    db.session.add(ticket)
    db.session.commit()
    
    status = SLAService.check_sla_status(ticket)
    assert status == SLAStatus.APPROACHING

def test_check_sla_status_active_breached(app):
    user = User(
        email="employee_test@tt.com",
        password_hash="test",
        full_name="Employee",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    
    # SLA for High is 8 hours. Let's make it 9 hours old.
    ticket = Ticket(
        title="Test Ticket",
        description="High ticket",
        category="General",
        priority=TicketPriority.HIGH,
        created_by_id=user.id,
        created_at=utcnow() - timedelta(hours=9)
    )
    db.session.add(ticket)
    db.session.commit()
    
    status = SLAService.check_sla_status(ticket)
    assert status == SLAStatus.BREACHED

def test_check_sla_status_resolved_achieved(app):
    user = User(
        email="employee_test@tt.com",
        password_hash="test",
        full_name="Employee",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    
    # SLA for Low is 48 hours. Created 5 hours ago, resolved 1 hour ago (within SLA)
    ticket = Ticket(
        title="Test Ticket",
        description="Low ticket",
        category="General",
        priority=TicketPriority.LOW,
        status=TicketStatus.RESOLVED,
        created_by_id=user.id,
        created_at=utcnow() - timedelta(hours=5),
        updated_at=utcnow() - timedelta(hours=1)
    )
    db.session.add(ticket)
    db.session.commit()
    
    # Add status history
    history = TicketStatusHistory(
        ticket_id=ticket.id,
        old_status=TicketStatus.OPEN,
        new_status=TicketStatus.RESOLVED,
        changed_by_id=user.id,
        changed_at=utcnow() - timedelta(hours=1)
    )
    db.session.add(history)
    db.session.commit()
    
    status = SLAService.check_sla_status(ticket)
    assert status == SLAStatus.ACHIEVED

def test_check_sla_status_resolved_breached(app):
    user = User(
        email="employee_test@tt.com",
        password_hash="test",
        full_name="Employee",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    
    # SLA for Critical is 4 hours. Created 6 hours ago, resolved 1 hour ago (resolved late)
    ticket = Ticket(
        title="Test Ticket",
        description="Critical ticket",
        category="General",
        priority=TicketPriority.CRITICAL,
        status=TicketStatus.RESOLVED,
        created_by_id=user.id,
        created_at=utcnow() - timedelta(hours=6),
        updated_at=utcnow() - timedelta(hours=1)
    )
    db.session.add(ticket)
    db.session.commit()
    
    history = TicketStatusHistory(
        ticket_id=ticket.id,
        old_status=TicketStatus.OPEN,
        new_status=TicketStatus.RESOLVED,
        changed_by_id=user.id,
        changed_at=utcnow() - timedelta(hours=1)
    )
    db.session.add(history)
    db.session.commit()
    
    status = SLAService.check_sla_status(ticket)
    assert status == SLAStatus.BREACHED
