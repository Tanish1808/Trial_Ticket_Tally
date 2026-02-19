from flask import Flask, jsonify
from flask_cors import CORS
from app.core.config import Config
from app.core.config import Config
from app.core.database import db, migrate
from app.websocket.ticket_socket import register_socket_events
from app.core.extensions import socketio

# Global Extensions
# socketio moved to app.core.extensions

def create_app():
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')
    
    print(f" * Template Dir: {template_dir}")
    print(f" * Static Dir: {static_dir}")
    print(f" * Template Dir Exists? {os.path.exists(template_dir)}")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(Config)

    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    socketio.init_app(app)
    from app.core.extensions import scheduler
    scheduler.init_app(app)
    scheduler.start()
    
    # Register Scheduled Jobs
    from app.services.ticket_service import TicketService
    
    @scheduler.task('interval', id='auto_close_tickets', days=1, misfire_grace_time=900)
    def auto_close_job():
        with app.app_context():
            TicketService.auto_close_resolved_tickets()
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

    # Global Error Handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e
        return jsonify({"error": str(e)}), 500


    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
