from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from app.schemas.auth_schema import SignupRequest, LoginRequest
from pydantic import ValidationError
from app.core.extensions import limiter

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

@auth_bp.route('/signup', methods=['POST'])
@limiter.limit("5 per minute")
def signup():
    """
    User Registration
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
            - full_name
            - role
          properties:
            email:
              type: string
              format: email
              example: user@example.com
            password:
              type: string
              minLength: 6
              example: securepassword123
            full_name:
              type: string
              example: John Doe
            department:
              type: string
              example: Engineering
            role:
              type: string
              enum: [EMPLOYEE, IT_STAFF, ADMIN]
              example: EMPLOYEE
            team_id:
              type: integer
              example: 1
    responses:
      201:
        description: User registered successfully
        schema:
          type: object
          properties:
            message:
              type: string
            access_token:
              type: string
            user:
              type: object
              properties:
                id:
                  type: integer
                email:
                  type: string
                role:
                  type: string
                name:
                  type: string
      400:
        description: Validation or value error
      500:
        description: Internal server error
    """
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
@limiter.limit("5 per minute")
def login():
    """
    User Login
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
              example: user@example.com
            password:
              type: string
              example: securepassword123
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            access_token:
              type: string
            user:
              type: object
              properties:
                id:
                  type: integer
                email:
                  type: string
                role:
                  type: string
                name:
                  type: string
      400:
        description: Validation error
      401:
        description: Invalid credentials
    """
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
@limiter.limit("3 per minute")
def forgot_password():
    """
    Request Password Reset Link
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              example: user@example.com
    responses:
      200:
        description: Reset email sent notification
        schema:
          type: object
          properties:
            message:
              type: string
      400:
        description: Missing email parameter
    """
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    AuthService.initiate_password_reset(email)
    
    return jsonify({"message": "If an account exists with this email, a password reset link has been sent."})

@auth_bp.route('/reset-password', methods=['POST'])
@limiter.limit("3 per minute")
def reset_password():
    """
    Reset Password using Token
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - token
            - new_password
          properties:
            token:
              type: string
              example: token-string-from-email
            new_password:
              type: string
              minLength: 6
              example: newsecurepass123
    responses:
      200:
        description: Password reset successful
        schema:
          type: object
          properties:
            message:
              type: string
      400:
        description: Validation or token error
    """
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
    """
    Login as Demo Employee
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            access_token:
              type: string
            user:
              type: object
              properties:
                id:
                  type: integer
                email:
                  type: string
                role:
                  type: string
                name:
                  type: string
      500:
        description: Internal server error
    """
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
