"""OAuth 2.0 token endpoint schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    """OAuth 2.0 token request."""

    grant_type: str = Field(..., description="OAuth 2.0 grant type")
    client_id: str = Field(..., description="Client identifier")
    client_secret: str = Field(..., description="Client secret")
    scope: Optional[str] = Field(default=None, description="Requested scope")


class TokenResponse(BaseModel):
    """OAuth 2.0 token response."""

    access_token: str = Field(..., description="Access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    scope: Optional[str] = Field(default=None, description="Granted scope")


class TokenError(BaseModel):
    """OAuth 2.0 error response."""

    error: str = Field(..., description="Error code")
    error_description: Optional[str] = Field(
        None,
        description="Human-readable error description"
    )
