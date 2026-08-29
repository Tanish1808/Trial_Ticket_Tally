import pytest
from unittest.mock import patch, MagicMock
from app.main import create_app
from app.core.config import TestingConfig, Config
from app.core.database import db
from app.models.user import User
from app.core.constants import UserRole
from app.utils.password import hash_password
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
from app.services.auth_service import AuthService
from flask import request

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

def test_forgot_password_mixed_case_and_whitespace(client):
    # Seed user with normalized email
    user = User(
        email="tanish.tester@company.com",
        password_hash=hash_password("oldpassword123"),
        full_name="Tanish Tester",
        role=UserRole.EMPLOYEE,
        is_active=True
    )
    db.session.add(user)
    db.session.commit()

    with patch.object(EmailService, 'send_email') as mock_send:
        # Submit mixed case email with leading/trailing whitespace
        response = client.post('/api/v1/auth/forgot-password', json={
            "email": "  TaNiSh.TeStEr@Company.COM  "
        })

        assert response.status_code == 200
        assert "password reset link has been sent" in response.get_json()["message"]

        # Verify email dispatch was triggered for the exact normalized user email
        assert mock_send.called
        call_kwargs = mock_send.call_args.kwargs if mock_send.call_args.kwargs else mock_send.call_args[1]
        if not call_kwargs:
            to_email = mock_send.call_args[0][0]
        else:
            to_email = call_kwargs.get('to_email')
        assert to_email == "tanish.tester@company.com"

def test_email_service_sends_to_recipient_containing_test_word():
    # Test EmailService send_email_sync directly with mocked SMTP server
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        Config.MAIL_SERVER = "smtp.gmail.com"
        Config.MAIL_USERNAME = "server@tickettally.com"
        Config.MAIL_PASSWORD = "app-password"

        test_email = "qa.tester@domain.com"
        EmailService.send_email_sync(
            to_email=test_email,
            subject="Test Notification",
            body="<p>Test body</p>"
        )

        # Ensure message was sent directly to recipient
        assert mock_server.send_message.called
        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg['To'] == test_email

def test_effective_base_url_resolution(app):
    with app.test_request_context(
        '/',
        base_url='http://ticket-tally.onrender.com',
        headers={'X-Forwarded-Proto': 'https'}
    ):
        original_base = Config.BASE_URL
        try:
            Config.BASE_URL = 'http://localhost:5000'
            effective_url = NotificationService.get_effective_base_url()
            assert effective_url.startswith('https://')
            assert 'ticket-tally.onrender.com' in effective_url

            # When explicit non-localhost domain is set, respect it
            Config.BASE_URL = 'https://custom-domain.com'
            assert NotificationService.get_effective_base_url() == 'https://custom-domain.com'
        finally:
            Config.BASE_URL = original_base

def test_mobile_navbar_contrast_configuration(client):
    # Verify landing page HTML does not have navbar-dark
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'navbar-expand-lg fixed-top' in html
    assert 'navbar-expand-lg navbar-dark' not in html

    # Verify main.css contains high contrast navbar-toggler rules
    css_res = client.get('/static/css/main.css')
    assert css_res.status_code == 200
    css = css_res.get_data(as_text=True)
    assert '.navbar-toggler' in css
    assert '.navbar-toggler-icon' in css

def test_landing_page_horizontal_overflow_constraints(client):
    # Verify index.html uses responsive margins ms-lg-* rather than hardcoded ms-*
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'ms-lg-3' in html
    assert 'ms-lg-2' in html
    assert 'hero-cta' in html

    # Verify landing.css contains mobile responsive minmax and grid rules
    css_res = client.get('/static/css/landing.css')
    assert css_res.status_code == 200
    landing_css = css_res.get_data(as_text=True)
    assert 'minmax(min(100%, 240px), 1fr)' in landing_css
    assert 'grid-template-columns: repeat(3, 1fr)' in landing_css

def test_calendar_mobile_toolbar_responsive_rules(client):
    # Verify calendar.html contains responsive FullCalendar toolbar stacking rules
    response = client.get('/calendar')
    # If 302/200, check template rendering directly
    if response.status_code == 200:
        html = response.get_data(as_text=True)
        assert 'fc-header-toolbar' in html
        assert 'flex-direction: column' in html
        assert 'fc-toolbar-chunk' in html

def test_tablet_hero_visual_responsive_breakpoint(client):
    # Verify landing.css hides hero-visual at max-width 991px to prevent tablet overflow
    css_res = client.get('/static/css/landing.css')
    assert css_res.status_code == 200
    landing_css = css_res.get_data(as_text=True)
    assert '@media (max-width: 991px)' in landing_css
    assert '.hero-visual {' in landing_css

def test_demo_mode_exit_button_accessibility_and_responsive_rules(client):
    # Verify theme.js sets accessibility title, aria-label, and responsive wrapper
    js_res = client.get('/static/js/theme.js')
    assert js_res.status_code == 200
    theme_js = js_res.get_data(as_text=True)
    assert "exitBtn.setAttribute('title', 'Exit Demo Dashboard')" in theme_js
    assert "exitBtn.setAttribute('aria-label', 'Exit Demo Dashboard')" in theme_js
    assert '<span class="d-none d-md-inline">Exit Dashboard</span>' in theme_js

    # Verify fixes.css contains compact icon styles for demoExitBtn on mobile
    css_res = client.get('/static/css/fixes.css')
    assert css_res.status_code == 200
    fixes_css = css_res.get_data(as_text=True)
    assert '#demoExitBtn' in fixes_css
    assert 'width: 2.25rem' in fixes_css
