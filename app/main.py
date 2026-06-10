from flask import Flask, jsonify
from flask_cors import CORS
from app.core.config import Config
from app.core.config import Config
from app.core.database import db, migrate
from app.websocket.ticket_socket import register_socket_events
from app.core.extensions import socketio

# Global Extensions
# socketio moved to app.core.extensions

def create_app(config_class=Config):
    import os
    import logging
    import json

    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "message": record.getMessage(),
                "name": record.name,
                "filename": record.filename,
                "lineno": record.lineno,
            }
            if record.exc_info:
                log_record["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(log_record)

    # Configure Logging
    handler = logging.StreamHandler()
    if os.getenv('FLASK_ENV') == 'production' or os.getenv('JSON_LOGGING') == 'True':
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(handler)

    logger = logging.getLogger(__name__)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')
    
    logger.info(f"Template Dir: {template_dir}")
    logger.info(f"Static Dir: {static_dir}")
    logger.info(f"Template Dir Exists? {os.path.exists(template_dir)}")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(config_class)

    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    allowed_origins = app.config.get('CORS_ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000')
    if allowed_origins != '*':
        if isinstance(allowed_origins, str):
            allowed_origins = [orig.strip() for orig in allowed_origins.split(',') if orig.strip()]
    CORS(app, origins=allowed_origins)
    
    redis_url = app.config.get('REDIS_URL')
    socketio.init_app(
        app,
        cors_allowed_origins=allowed_origins,
        message_queue=redis_url if redis_url else None
    )
    # Configure Swagger UI Options
    app.config['SWAGGER'] = {
        'title': 'Ticket-Tally API Documentation',
        'uiversion': 3,
        'specs_route': '/api/docs',
        'static_url_path': '/flasgger_static'
    }

    from app.core.extensions import scheduler, limiter
    limiter.init_app(app)
    scheduler.init_app(app)
    if not app.config.get('TESTING'):
        scheduler.start()

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec_v1',
                "route": '/api/docs/spec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda model: True,
            }
        ],
        "swagger_ui": True,
        "specs_route": "/api/docs"
    }

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Ticket-Tally API",
            "description": "Comprehensive REST API for Ticket-Tally ITSM Platform.",
            "version": "1.0.0"
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
            }
        },
        "security": [
            {
                "Bearer": []
            }
        ]
    }
    from flasgger import Swagger
    Swagger(app, config=swagger_config, template=swagger_template)
    
    # Register Scheduled Jobs
    from app.services.ticket_service import TicketService
    
    if not app.config.get('TESTING'):
        @scheduler.task('interval', id='auto_close_tickets', days=1, misfire_grace_time=900)
        def auto_close_job():
            with app.app_context():
                TicketService.auto_close_resolved_tickets()

        @scheduler.task('interval', id='archive_and_purge_tickets', days=1, misfire_grace_time=900)
        def archive_and_purge_job():
            with app.app_context():
                TicketService.archive_and_purge_old_tickets()
    from app.api.v1.auth_routes import auth_bp
    from app.api.v1.ticket_routes import ticket_bp
    from app.api.v1.user_routes import user_bp
    from app.api.v1.admin_routes import admin_bp
    from app.api.v1.it_staff_routes import it_staff_bp
    from app.api.v1.analytics_routes import analytics_bp
    from app.web_routes import web_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ticket_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(it_staff_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(web_bp)
    
    from app.api.v1.project_routes import project_bp
    app.register_blueprint(project_bp)

    from app.api.v1.notification_routes import notification_bp
    app.register_blueprint(notification_bp, url_prefix='/api/v1/notifications')

    # Register Socket Events
    register_socket_events(socketio)

    # Rate Limit Error Handler
    from flask_limiter.errors import RateLimitExceeded
    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_exceeded(e):
        return jsonify({"error": f"Too Many Requests: {e.description}"}), 429

    # Global Error Handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e
        return jsonify({"error": str(e)}), 500

    # Trigger once on startup to process existing old tickets
    # Doing this at the very end ensures all models and blueprints are loaded
    if not app.config.get('TESTING'):
        with app.app_context():
            try:
                from app.services.ticket_service import TicketService
                logger.info("Pre-starting auto-close job on application startup...")
                TicketService.auto_close_resolved_tickets()
                logger.info("Pre-starting data retention purge job on application startup...")
                TicketService.archive_and_purge_old_tickets()
            except Exception as e:
                logger.error(f"Failed to run startup jobs: {e}")

    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
