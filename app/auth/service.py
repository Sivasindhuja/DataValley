import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException, Depends
from typing import Optional
from app.config import settings
from app.auth.models import AuthContext

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_access_token(customer_id: str, roles=None, expires_minutes: Optional[int] = None) -> str:
    if roles is None:
        roles = ["customer"]
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)
    payload = {
        "sub": customer_id,
        "customer_id": customer_id,
        "roles": roles,
        "exp": exp,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> AuthContext:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return AuthContext(
            authenticated=True,
            user_id=payload.get("sub"),
            customer_id=payload.get("customer_id") or payload.get("sub"),
            roles=payload.get("roles", ["customer"]),
            token=token,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

async def get_current_auth(authorization: Optional[str] = Header(default=None)) -> AuthContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.replace("Bearer ", "", 1).strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    return decode_access_token(token)

def get_optional_auth(authorization: Optional[str] = Header(default=None)) -> Optional[AuthContext]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.replace("Bearer ", "", 1).strip()
    try:
        return decode_access_token(token)
    except:
        return None
