from flask_socketio import emit
from flask import request
# Note: SocketIO events are registered in main or via Blueprint-like structure if using extension.
# Here we define handlers that can be imported or registered.
# For simplicity in this structure, we'll define a function to register events.

def register_socket_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        print(f"Client connected: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"Client disconnected: {request.sid}")
    
    # Custom events if needed, e.g. client sending message
    # Most logic is server->client (emitting) which is done in Services.
