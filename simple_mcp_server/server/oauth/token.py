from datetime import datetime, timedelta, timezone
from jose import jwt
from config import get_settings

settings = get_settings()


def create_access_token(client_id: str) -> tuple[str, int]:
    """
    Create JWT access token
    Returns: (token, expires_in_seconds)
    """
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta

    claims = {
        "sub": client_id,
        "aud": settings.SERVER_URI,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "scope": "mcp:tools"
    }

    token = jwt.encode(claims, settings.SECRET_KEY, algorithm="HS256")
    return token, int(expires_delta.total_seconds())


def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token
    Raises: JWTError if invalid
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=["HS256"],
        audience=settings.SERVER_URI
    )
