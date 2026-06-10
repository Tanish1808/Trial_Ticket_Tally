import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.core.constants import UserRole
from app.utils.jwt import create_access_token

class RateLimitTestConfig(TestingConfig):
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"

@pytest.fixture
def app():
    # Use config with rate limiting enabled
    app = create_app(RateLimitTestConfig)
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
        email="limiter_user@tt.com",
        password_hash="test",
        full_name="Limiter User",
        role=UserRole.EMPLOYEE
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}

def test_login_rate_limiting(client):
    # Endpoint has @limiter.limit("5 per minute")
    # Send 5 login requests (will return 400/401, but they count towards rate limiting)
    for _ in range(5):
        response = client.post('/api/v1/auth/login', json={"email": "wrong@tt.com", "password": "wrong"})
        # Should be 401 Unauthorized, NOT 429
        assert response.status_code == 401
    
    # 6th request should be rate limited (429 Too Many Requests)
    response_limited = client.post('/api/v1/auth/login', json={"email": "wrong@tt.com", "password": "wrong"})
    assert response_limited.status_code == 429
    assert "Too Many Requests" in response_limited.get_json().get("error", "")

def test_ticket_creation_rate_limiting(client, auth_headers):
    # Endpoint has @limiter.limit("10 per minute")
    # Send 10 ticket creation requests (e.g. invalid request format, will return 400, but counts towards rate limiting)
    for _ in range(10):
        response = client.post('/api/v1/tickets', json={}, headers=auth_headers)
        # Should be 400 Bad Request (Pydantic validation error), NOT 429
        assert response.status_code == 400
    
    # 11th request should be rate limited (429 Too Many Requests)
    response_limited = client.post('/api/v1/tickets', json={}, headers=auth_headers)
    assert response_limited.status_code == 429
    assert "Too Many Requests" in response_limited.get_json().get("error", "")
