from flask_socketio import SocketIO
from flask_apscheduler import APScheduler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

socketio = SocketIO()
scheduler = APScheduler()
limiter = Limiter(key_func=get_remote_address)


