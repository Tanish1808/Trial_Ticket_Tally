import os
import re

TEMPLATES_DIR = r"d:/Trial_Ticket_Tally_01/app/templates"

def refactor_html():
    if not os.path.exists(TEMPLATES_DIR):
        print(f"Directory not found: {TEMPLATES_DIR}")
        return

    print(f"Scanning {TEMPLATES_DIR}...")
    files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".html")]
    print(f"Found {len(files)} HTML files: {files}")

    for filename in files:
        filepath = os.path.join(TEMPLATES_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Replace static assets
        # Regex to handle both " and ' naming
        content = re.sub(r'href=["\']static/css/([^"\']+)["\']', r'href="{{ url_for(\'static\', filename=\'css/\1\') }}"', content)
        content = re.sub(r'src=["\']static/js/([^"\']+)["\']', r'src="{{ url_for(\'static\', filename=\'js/\1\') }}"', content)
        content = re.sub(r'src=["\']static/img/([^"\']+)["\']', r'src="{{ url_for(\'static\', filename=\'img/\1\') }}"', content)
        
        # 2. Replace page links
        # This map covers all known pages
        routes = {
            "index.html": "web.index",
            "templates/login.html": "web.login",
            "login.html": "web.login",
            "templates/signup.html": "web.signup",
            "signup.html": "web.signup",
            "templates/admin-dashboard.html": "web.admin_dashboard",
            "admin-dashboard.html": "web.admin_dashboard",
            "templates/employee-dashboard.html": "web.employee_dashboard",
            "employee-dashboard.html": "web.employee_dashboard",
            "templates/itstaff-dashboard.html": "web.itstaff_dashboard",
            "itstaff-dashboard.html": "web.itstaff_dashboard",
            "templates/profile.html": "web.profile",
            "profile.html": "web.profile",
            "templates/projects.html": "web.projects",
            "projects.html": "web.projects",
            "templates/ticket-details.html": "web.ticket_details",
            "ticket-details.html": "web.ticket_details"
        }
        
        for link, endpoint in routes.items():
            # Avoid double-templating if already fixed
            if f"url_for('{endpoint}')" in content:
                continue
                
            content = content.replace(f'href="{link}"', f'href="{{{{ url_for(\'{endpoint}\') }}}}"')
            content = content.replace(f"href='{link}'", f"href='{{{{ url_for('{endpoint}') }}}}'")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Refactored {filename}")

if __name__ == "__main__":
    refactor_html()
