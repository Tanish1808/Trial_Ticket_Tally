import jwt
import datetime
from app.core.config import Config

def create_access_token(identity: dict, expires_in: int = None) -> str:
    if expires_in is None:
        expires_in = Config.JWT_ACCESS_TOKEN_EXPIRES
    
    payload = {
        "sub": identity,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
    }
    
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
