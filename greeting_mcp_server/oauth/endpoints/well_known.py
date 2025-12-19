"""OAuth 2.0 Authorization Server Metadata (RFC 8414) endpoint."""

from fastapi import APIRouter

router = APIRouter()

# Configuration
BASE_URL = "http://localhost:8000"


@router.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata():
    """OAuth 2.0 Authorization Server Metadata endpoint (RFC 8414).

    Provides discovery information about the OAuth authorization server.
    MCP clients use this to discover token and registration endpoints.

    Returns:
        Authorization server metadata
    """
    return {
        "issuer": BASE_URL,
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "registration_endpoint": f"{BASE_URL}/register",
        "jwks_uri": f"{BASE_URL}/.well-known/jwks.json",
        "response_types_supported": ["token"],
        "grant_types_supported": ["client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": ["mcp:tools"],
        "service_documentation": "https://gofastmcp.com/servers/auth/remote-oauth"
    }
