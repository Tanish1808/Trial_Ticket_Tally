import os
import sys

# Ensure root is in path
sys.path.append(os.getcwd())

from app.main import create_app
from flask import render_template

def debug_app():
    print(f"Current Working Directory: {os.getcwd()}")
    expected_path = os.path.join(os.getcwd(), 'app', 'templates', 'index.html')
    print(f"Checking for index.html at: {expected_path}")
    print(f"File Exists: {os.path.exists(expected_path)}")
    
    app = create_app()
    print(f"Flask Configured Template Folder: {app.template_folder}")
    
    with app.app_context():
        try:
            print("Attempting to render 'index.html'...")
            render_template('index.html')
            print("SUCCESS: 'index.html' rendered successfully.")
        except Exception as e:
            print(f"FAILURE: Could not render template. Error: {e}")
            # Try to inspect loader
            if hasattr(app.jinja_loader, 'searchpath'):
                print(f"Jinja Search Paths: {app.jinja_loader.searchpath}")
            else:
                print("Could not retrieve Jinja searchpaths.")

if __name__ == "__main__":
    debug_app()
