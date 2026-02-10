from functools import wraps
from flask import request, jsonify, g
from app.utils.jwt import decode_token
from app.models.user import User
from app.core.constants import UserRole

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            payload = decode_token(token)
            current_user = User.query.get(int(payload['sub']))
            if not current_user:
                raise Exception("User not found")
            g.user = current_user
        except Exception as e:
            return jsonify({'message': str(e)}), 401
        
        return f(*args, **kwargs)
    return decorated

def role_required(roles: list[UserRole]):
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated_function(*args, **kwargs):
            if g.user.role not in roles:
                return jsonify({'message': 'Permission denied'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
