import pytest
from app.main import create_app
from app.core.config import TestingConfig
from app.core.database import db
from app.models.user import User
from app.core.constants import UserRole
from app.utils.password import hash_password
from app.utils.token import generate_reset_token

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

def test_signup_success(client):
    # Test valid user registration
    signup_data = {
        "email": "new_user@tt.com",
        "password": "securepassword123",
        "full_name": "New User",
        "department": "Engineering",
        "role": "employee"
    }
    response = client.post('/api/v1/auth/signup', json=signup_data)
    assert response.status_code == 201
    
    data = response.get_json()
    assert data["message"] == "User registered successfully"
    assert "access_token" in data
    assert data["user"]["email"] == "new_user@tt.com"
    assert data["user"]["role"] == "employee"

def test_signup_duplicate_email(client):
    # Register first user
    signup_data = {
        "email": "duplicate@tt.com",
        "password": "securepassword123",
        "full_name": "Duplicate User",
        "role": "employee"
    }
    response1 = client.post('/api/v1/auth/signup', json=signup_data)
    assert response1.status_code == 201

    # Attempt to register second user with same email
    response2 = client.post('/api/v1/auth/signup', json=signup_data)
    assert response2.status_code == 400
    assert "error" in response2.get_json()

def test_signup_validation_errors(client):
    # Test invalid email format
    invalid_email_data = {
        "email": "invalid-email-format",
        "password": "securepassword123",
        "full_name": "Invalid Email User",
        "role": "employee"
    }
    response = client.post('/api/v1/auth/signup', json=invalid_email_data)
    assert response.status_code == 400

def test_login_success(client):
    # Seed user in DB
    user = User(
        email="login_user@tt.com",
        password_hash=hash_password("correctpassword"),
        full_name="Login User",
        role=UserRole.EMPLOYEE,
        is_active=True
    )
    db.session.add(user)
    db.session.commit()

    # Login with valid credentials
    login_data = {
        "email": "login_user@tt.com",
        "password": "correctpassword"
    }
    response = client.post('/api/v1/auth/login', json=login_data)
    assert response.status_code == 200
    
    data = response.get_json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_user@tt.com"

def test_login_invalid_credentials(client):
    # Seed user in DB
    user = User(
        email="login_fail@tt.com",
        password_hash=hash_password("correctpassword"),
        full_name="Fail User",
        role=UserRole.EMPLOYEE,
        is_active=True
    )
    db.session.add(user)
    db.session.commit()

    # Login with incorrect password
    invalid_pass_data = {
        "email": "login_fail@tt.com",
        "password": "wrongpassword"
    }
    response1 = client.post('/api/v1/auth/login', json=invalid_pass_data)
    assert response1.status_code == 401

    # Login with non-existent email
    non_existent_data = {
        "email": "nonexistent@tt.com",
        "password": "correctpassword"
    }
    response2 = client.post('/api/v1/auth/login', json=non_existent_data)
    assert response2.status_code == 401

def test_login_disabled_account(client):
    # Seed a deactivated user in DB
    user = User(
        email="disabled@tt.com",
        password_hash=hash_password("correctpassword"),
        full_name="Disabled User",
        role=UserRole.EMPLOYEE,
        is_active=False
    )
    db.session.add(user)
    db.session.commit()

    login_data = {
        "email": "disabled@tt.com",
        "password": "correctpassword"
    }
    response = client.post('/api/v1/auth/login', json=login_data)
    assert response.status_code == 401
    assert "Account disabled" in response.get_json()["error"]

def test_forgot_password_always_returns_success(client):
    # Test checking for account enumeration vulnerability
    forgot_data = {
        "email": "anyemail@tt.com"
    }
    response = client.post('/api/v1/auth/forgot-password', json=forgot_data)
    assert response.status_code == 200
    assert "password reset link has been sent" in response.get_json()["message"]

def test_complete_password_reset_success(client):
    # Seed user in DB
    user = User(
        email="reset_me@tt.com",
        password_hash=hash_password("oldpassword"),
        full_name="Reset User",
        role=UserRole.EMPLOYEE,
        is_active=True
    )
    db.session.add(user)
    db.session.commit()

    # Generate timing token
    token = generate_reset_token(user.email)

    # Perform password reset
    reset_data = {
        "token": token,
        "new_password": "newsecurepassword123"
    }
    response = client.post('/api/v1/auth/reset-password', json=reset_data)
    assert response.status_code == 200
    assert "Password reset successfully" in response.get_json()["message"]

    # Verify we can login with new password
    login_data = {
        "email": "reset_me@tt.com",
        "password": "newsecurepassword123"
    }
    response_login = client.post('/api/v1/auth/login', json=login_data)
    assert response_login.status_code == 200

def test_demo_login(client):
    # Call demo login route
    response = client.post('/api/v1/auth/demo-login')
    assert response.status_code == 200
    
    data = response.get_json()
    assert "access_token" in data
    assert data["user"]["email"] == "demo@tickettally.com"
    assert data["user"]["role"] == "employee"
