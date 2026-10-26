"""JWT and password hashing utilities for Dashboard authentication."""

from datetime import datetime, timedelta
from typing import Optional, Any
import hashlib

from app.config import settings

# JWT library fallback: try python-jose first, then PyJWT
try:
    from jose import JWTError, jwt
except ImportError:
    try:
        import jwt
        from jwt.exceptions import PyJWTError as JWTError
    except ImportError:
        jwt = None
        class JWTError(Exception):
            pass

# Password hasher: try passlib first, then fallback to SHA-256
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        """Hash a plain text password using bcrypt."""
        return pwd_context.hash(password)

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hash."""
        if hashed_password.startswith("sha256$"):
            return hashed_password == ("sha256$" + hashlib.sha256(plain_password.encode()).hexdigest())
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

except ImportError:
    def hash_password(password: str) -> str:
        """Fallback SHA-256 password hashing."""
        return "sha256$" + hashlib.sha256(password.encode()).hexdigest()

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against fallback hash."""
        return hashed_password == ("sha256$" + hashlib.sha256(plain_password.encode()).hexdigest())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT token."""
    to_encode = data.copy()
    expire_minutes = getattr(settings, "JWT_EXPIRE_MINUTES", 480)
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=expire_minutes))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    secret = getattr(settings, "DASHBOARD_SECRET_KEY", settings.SECRET_KEY)
    algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=algorithm)
    # PyJWT returns str in modern versions, but ensure str type
    return encoded_jwt if isinstance(encoded_jwt, str) else encoded_jwt.decode("utf-8")


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a signed JWT token."""
    secret = getattr(settings, "DASHBOARD_SECRET_KEY", settings.SECRET_KEY)
    algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except Exception:
        return None
