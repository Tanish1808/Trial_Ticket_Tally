
import urllib.request
import urllib.error
import json
import ssl

# Configuration
BASE_URL = "http://127.0.0.1:5000/api/v1"
ADMIN_EMAIL = "admin@tt.com"
ADMIN_PASSWORD = "admin"

def make_request(url, method='GET', data=None, token=None):
    req = urllib.request.Request(url, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.data = json_data

    try:
        # Ignore SSL for localhost
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def test_restriction():
    print("Logging in...")
    status, body = make_request(f"{BASE_URL}/auth/login", method='POST', data={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if status != 200:
        print(f"Login failed: {body}")
        return

    token = body['token']
    print("Login successful.")

    # 1. Create Project
    print("Creating test project...")
    project_data = {
        "name": "Test Restriction Project",
        "description": "Testing locked status",
        "status": "Active",
        "priority": "Low",
        "startDate": "2026-01-01",
        "deadline": "2026-12-31"
    }
    status, body = make_request(f"{BASE_URL}/projects", method='POST', data=project_data, token=token)
    
    if status != 201:
        print(f"Failed to create project: {body}")
        return
        
    project_id = body['id']
    print(f"Created Project ID: {project_id}")

    # 2. Mark as Completed
    print("Marking as Completed...")
    status, body = make_request(f"{BASE_URL}/projects/{project_id}", method='PATCH', data={"status": "Completed"}, token=token)
    if status != 200:
        print(f"Failed to mark completed: {body}")
        return
    print("Project marked as Completed.")

    # 3. Attempt Edit
    print("Attempting to edit description (Should Fail)...")
    status, body = make_request(f"{BASE_URL}/projects/{project_id}", method='PATCH', data={"description": "Hacked"}, token=token)
    
    if status == 400:
        print("SUCCESS: Edit blocked with 400 Bad Request")
        print(f"Response: {body}")
    else:
        print(f"FAILURE: Edit allowed! Status: {status}")
        print(f"Response: {body}")

    # Cleanup
    print("Cleaning up...")
    make_request(f"{BASE_URL}/projects/{project_id}", method='DELETE', token=token)
    print("Done.")

if __name__ == "__main__":
    test_restriction()
