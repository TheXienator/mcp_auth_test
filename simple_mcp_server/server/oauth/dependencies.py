from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from server.oauth.token import verify_token
from config import get_settings

settings = get_settings()
security = HTTPBearer()


async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """FastAPI dependency for token validation"""
    try:
        payload = verify_token(credentials.credentials)
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={
                "WWW-Authenticate": f'Bearer realm="{settings.SERVER_URI}/.well-known/mcp-resource-metadata.json"'
            }
        )
