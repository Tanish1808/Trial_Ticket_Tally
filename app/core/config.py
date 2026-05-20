import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///ticket_tally.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default-jwt-secret')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    
    # Upload config for PDF or attachments if needed
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

    BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

    # CORS Allowed Origins (comma-separated string)
    CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000')

    # Demo User Configuration
    DEMO_EMAIL = "demo@tickettally.com"
    DEMO_PASSWORD = "demo_password_secure_2026"

    # Redis and Rate Limiting
    REDIS_URL = os.getenv('REDIS_URL')
    RATELIMIT_STORAGE_URI = REDIS_URL if REDIS_URL else 'memory://'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    RATELIMIT_ENABLED = False
    REDIS_URL = None
    RATELIMIT_STORAGE_URI = 'memory://'

