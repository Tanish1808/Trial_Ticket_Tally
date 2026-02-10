
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

def test():
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

    # 1. Test Search
    print("Testing User Search...")
    # Assuming 'Admin' exists
    status, body = make_request(f"{BASE_URL}/users?search=Admin", token=token)
    if status == 200 and len(body) > 0:
        print(f"SUCCESS: Search found {len(body)} users.")
        print(f"First match: {body[0]['full_name']} ({body[0]['email']})")
    else:
        print(f"FAILURE: Search failed. Status: {status}, Body: {body}")

    # 2. Test Assignment by Name
    print("Testing Assignment by Name...")
    # Create a dummy project
    project_data = {
        "name": "Team Assign Test",
        "description": "Testing Name Assignment",
        "status": "Active",
        "priority": "Low",
        "startDate": "2026-02-01",
        "deadline": "2026-03-01",
        "team": [
            {"name": "Admin User"} # Assuming Admin User is the name of admin
        ]
    }
    
    # We need to know a valid user name. Admin is usually "Admin User"? 
    # Let's check who we logged in as.
    status, me = make_request(f"{BASE_URL}/users/me", token=token)
    my_name = me['full_name']
    print(f"Targeting user: {my_name}")
    
    project_data['team'] = [{"name": my_name}]

    status, body = make_request(f"{BASE_URL}/projects", method='POST', data=project_data, token=token)
    
    if status == 201:
        project = body
        team = project.get('team', [])
        found = any(m['email'] == ADMIN_EMAIL for m in team)
        if found:
            print(f"SUCCESS: Project created and user assigned by Name ({my_name}).")
        else:
            print("FAILURE: Project created but user NOT assigned.")
            print(f"Team members: {team}")
            
        # Cleanup
        make_request(f"{BASE_URL}/projects/{project['id']}", method='DELETE', token=token)
    else:
        print(f"FAILURE: Project creation failed. Status: {status}, Body: {body}")

if __name__ == "__main__":
    test()
