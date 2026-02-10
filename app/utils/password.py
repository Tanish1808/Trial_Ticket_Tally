import hashlib
import os

def hash_password(password: str) -> str:
    # Using simple pbkdf2 for standard library compat or werkzeug if available. 
    # Since flask is required, werkzeug is available.
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)

def verify_password(stored_hash: str, password: str) -> bool:
    from werkzeug.security import check_password_hash
    return check_password_hash(stored_hash, password)
