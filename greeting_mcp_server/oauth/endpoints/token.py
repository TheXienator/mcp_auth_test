"""OAuth 2.0 token endpoint."""

from datetime import timedelta
from fastapi import APIRouter, Form, HTTPException, status
from oauth.jwt_utils import get_or_create_keypair, create_access_token, DEFAULT_KID
from oauth.storage import get_storage
from oauth.schemas.token import TokenResponse, TokenError

router = APIRouter()

# Configuration (could be loaded from env)
ISSUER = "http://localhost:8000"
AUDIENCE = "mcp-greeting-server"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


@router.post("/oauth/token", response_model=TokenResponse)
async def token_endpoint(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    scope: str = Form(default="mcp:tools")
):
    """OAuth 2.0 token endpoint.

    Supports client_credentials grant type.

    Args:
        grant_type: OAuth 2.0 grant type (must be "client_credentials")
        client_id: Client identifier
        client_secret: Client secret
        scope: Requested scope

    Returns:
        TokenResponse with access_token

    Raises:
        HTTPException: If grant type is unsupported or credentials are invalid
    """
    # Validate grant type
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=TokenError(
                error="unsupported_grant_type",
                error_description=f"Grant type '{grant_type}' is not supported"
            ).model_dump()
        )

    # Get storage
    storage = get_storage()

    # Validate client credentials
    if not storage.validate_credentials(client_id, client_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=TokenError(
                error="invalid_client",
                error_description="Invalid client credentials"
            ).model_dump()
        )

    # Get keypair
    private_key_pem, _ = get_or_create_keypair()

    # Create access token
    access_token = create_access_token(
        client_id=client_id,
        issuer=ISSUER,
        audience=AUDIENCE,
        private_key_pem=private_key_pem,
        kid=DEFAULT_KID,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        scope=scope
    )

    # Return token response
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        scope=scope
    )
