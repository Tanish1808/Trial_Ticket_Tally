from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from app.schemas.auth_schema import SignupRequest, LoginRequest
from pydantic import ValidationError

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = SignupRequest(**request.json)
        user = AuthService.register_user(data)
        
        # Auto-login after signup
        login_data = LoginRequest(email=data.email, password=data.password)
        login_result = AuthService.login_user(login_data)
        
        return jsonify({
            "message": "User registered successfully", 
            "access_token": login_result['access_token'],
            "user": {
                "id": login_result['user'].id,
                "email": login_result['user'].email,
                "role": login_result['user'].role.value,
                "name": login_result['user'].full_name
            }
        }), 201
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = LoginRequest(**request.json)
        result = AuthService.login_user(data)
        return jsonify({
            "access_token": result['access_token'],
            "user": {
                "id": result['user'].id,
                "email": result['user'].email,
                "role": result['user'].role.value,
                "name": result['user'].full_name
            }
        }), 200
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    AuthService.initiate_password_reset(email)
    
    return jsonify({"message": "If an account exists with this email, a password reset link has been sent."})

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return jsonify({"error": "Token and new password are required"}), 400
        
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
        
    try:
        AuthService.complete_password_reset(token, new_password)
        return jsonify({"message": "Password reset successfully. You can now login."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.route('/demo-login', methods=['POST'])
def demo_login():
    try:
        result = AuthService.login_demo_user()
        return jsonify({
            "access_token": result['access_token'],
            "user": {
                "id": result['user'].id,
                "email": result['user'].email,
                "role": result['user'].role.value,
                "name": result['user'].full_name
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
