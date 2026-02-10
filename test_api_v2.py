from app.main import create_app
from app.core.database import db
from app.models.user import User
from app.utils.jwt import create_access_token

app = create_app()

with app.app_context():
    # Get an admin user for the token
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        print("No admin found!")
        exit(1)
    
    # Generate token using internal util
    token = create_access_token(str(admin.id))
    
    client = app.test_client()
    # auth_middleware expects "Bearer <token>"
    response = client.get('/api/v1/users?role=employee', headers={
        'Authorization': f'Bearer {token}'
    })
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Data: {response.get_json()}")
