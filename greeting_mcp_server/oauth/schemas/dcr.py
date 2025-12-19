"""Dynamic Client Registration (RFC 7591) schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ClientRegistrationRequest(BaseModel):
    """RFC 7591 client registration request."""

    client_name: str = Field(..., description="Human-readable client name")
    redirect_uris: Optional[List[str]] = Field(
        default=None,
        description="List of redirect URIs"
    )
    grant_types: Optional[List[str]] = Field(
        default=["client_credentials"],
        description="OAuth 2.0 grant types"
    )
    token_endpoint_auth_method: Optional[str] = Field(
        default="client_secret_post",
        description="Token endpoint authentication method"
    )
    scope: Optional[str] = Field(
        default="mcp:tools",
        description="Requested scope"
    )


class ClientRegistrationResponse(BaseModel):
    """RFC 7591 client registration response."""

    client_id: str = Field(..., description="Unique client identifier")
    client_secret: str = Field(..., description="Client secret")
    client_name: str = Field(..., description="Client name")
    redirect_uris: List[str] = Field(..., description="Registered redirect URIs")
    grant_types: List[str] = Field(..., description="Allowed grant types")
    token_endpoint_auth_method: str = Field(
        default="client_secret_post",
        description="Token endpoint authentication method"
    )
    registration_access_token: str = Field(
        ...,
        description="Token for accessing client configuration endpoint"
    )
    registration_client_uri: str = Field(
        ...,
        description="URI for client configuration endpoint"
    )


class ClientRegistrationError(BaseModel):
    """RFC 7591 error response."""

    error: str = Field(..., description="Error code")
    error_description: Optional[str] = Field(
        None,
        description="Human-readable error description"
    )
