import os
import json
import pytest
import shutil
import tempfile
from datetime import datetime, timedelta
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.ticket_status_history import TicketStatusHistory
from app.core.constants import UserRole, TicketStatus
from app.services.ticket_service import TicketService
from app.utils.jwt import create_access_token

@pytest.fixture
def temp_archive():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@pytest.fixture
def app(temp_archive):
    app = create_app(TestingConfig)
    app.config['ARCHIVE_FOLDER'] = temp_archive
    # For testing, retention days is 30
    app.config['RETENTION_DAYS'] = 30
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

def test_archive_and_purge_service(app, temp_archive, test_user):
    with app.app_context():
        # Create a ticket
        ticket = Ticket(
            title="Old Closed Ticket",
            description="Should be purged and archived",
            category="Software Issue",
            status=TicketStatus.CLOSED,
            created_by_id=test_user.id
        )
        db.session.add(ticket)
        db.session.commit()

        # Add comment
        comment = Comment(
            ticket_id=ticket.id,
            user_id=test_user.id,
            text="This is a test comment"
        )
        db.session.add(comment)
        db.session.commit()

        # Artificially set updated_at back by 40 days
        ticket.updated_at = datetime.utcnow() - timedelta(days=40)
        db.session.commit()

        ticket_id = ticket.id

        # Run purge
        count = TicketService.archive_and_purge_old_tickets()
        assert count == 1

        # Check DB: ticket should be deleted
        purged_ticket = Ticket.query.execution_options(include_deleted=True).filter_by(id=ticket_id).first()
        assert purged_ticket is None

        # Check comment and history: should be cascaded and gone
        assert Comment.query.filter_by(ticket_id=ticket_id).first() is None
        assert TicketStatusHistory.query.filter_by(ticket_id=ticket_id).first() is None

        # Check archive JSON
        archive_path = os.path.join(temp_archive, f"ticket_archive_{ticket_id}.json")
        assert os.path.exists(archive_path)

        with open(archive_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data['id'] == ticket_id
            assert data['title'] == "Old Closed Ticket"
            assert len(data['comments']) == 1
            assert data['comments'][0]['text'] == "This is a test comment"

def test_soft_deleted_purge(app, temp_archive, test_user):
    with app.app_context():
        ticket = Ticket(
            title="Soft Deleted Ticket",
            description="Should be purged",
            category="Hardware Issue",
            status=TicketStatus.OPEN,
            created_by_id=test_user.id
        )
        db.session.add(ticket)
        db.session.commit()

        ticket_id = ticket.id

        # Soft delete it
        ticket.soft_delete()
        db.session.commit()

        # Set updated_at back
        ticket.updated_at = datetime.utcnow() - timedelta(days=40)
        db.session.commit()

        # Run purge
        count = TicketService.archive_and_purge_old_tickets()
        assert count == 1

        # Check DB
        assert Ticket.query.execution_options(include_deleted=True).filter_by(id=ticket_id).first() is None

        # Check file
        archive_path = os.path.join(temp_archive, f"ticket_archive_{ticket_id}.json")
        assert os.path.exists(archive_path)

def test_manual_purge_api(app, client, admin_headers, test_user):
    # Create ticket
    with app.app_context():
        ticket = Ticket(
            title="Manual Purge API Ticket",
            description="API purge test",
            category="Software Issue",
            status=TicketStatus.CLOSED,
            created_by_id=test_user.id
        )
        db.session.add(ticket)
        db.session.commit()

        ticket_id = ticket.id
        ticket.updated_at = datetime.utcnow() - timedelta(days=40)
        db.session.commit()

    # Trigger manual purge via API
    response = client.post('/api/v1/admin/purge', headers=admin_headers)
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data['status'] == "success"
    assert res_data['count'] == 1

    # Verify database
    with app.app_context():
        assert Ticket.query.execution_options(include_deleted=True).filter_by(id=ticket_id).first() is None
