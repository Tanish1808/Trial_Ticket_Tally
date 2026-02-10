import sys
print(f"DEBUG: Python Executable: {sys.executable}")
print(f"DEBUG: Python Path: {sys.path}")
try:
    import reportlab
    print(f"DEBUG: ReportLab IMPORTED SUCCESSFULLY: {reportlab.__file__}")
except ImportError as e:
    print(f"DEBUG: ReportLab IMPORT FAILED at startup: {e}")

from app.main import create_app, socketio

app = create_app()

if __name__ == '__main__':
    print("Starting server...")
    print(f"Access the application at: http://127.0.0.1:5000")
    print(f"DEBUG: BASE_URL from config: {app.config.get('BASE_URL')}")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
