from mcp.server.fastmcp import FastMCP
from fastmcp.server.auth import JWTVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl
import logging
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure auth settings
auth_settings = AuthSettings(
    issuer_url=AnyHttpUrl("http://localhost:8000"),  # OAuth issuer (same server)
    resource_server_url=AnyHttpUrl("http://localhost:8000")  # MCP server (same server)
)

# Configure JWT verification (points to ITSELF)
token_verifier = JWTVerifier(
    jwks_uri="http://localhost:8000/.well-known/jwks.json",  # Same server!
    issuer="http://localhost:8000",
    audience="mcp-greeting-server"
)

# Create MCP server with auth and token verification
mcp = FastMCP(
    "hello-server",
    auth=auth_settings,
    token_verifier=token_verifier,
    host="0.0.0.0",
    port=8000
)

# Helper function to add CORS headers to responses
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# OPTIONS handler for CORS preflight requests
@mcp.custom_route("/{path:path}", methods=["OPTIONS"])
async def options_handler(request):
    return add_cors_headers(JSONResponse({}))

# Tool is automatically protected
@mcp.tool()
def say_hello(name: str) -> str:
    """Return a personalized greeting.
    Args:
        name: The name of the person to greet.
    Returns:
        A friendly greeting string.
    """
    logger.info(f"say_hello called with name={name}")
    return f"Hello, {name}! Welcome to your authenticated MCP server."

# Add OAuth endpoints using custom_route
from starlette.responses import JSONResponse
from fastapi import HTTPException, status
from oauth.jwt_utils import get_or_create_keypair, create_access_token, public_key_to_jwk, DEFAULT_KID
from oauth.storage import get_storage
from oauth.schemas.token import TokenResponse, TokenError
from oauth.schemas.dcr import ClientRegistrationRequest, ClientRegistrationResponse, ClientRegistrationError
from datetime import timedelta
import secrets
import uuid
from pathlib import Path

# Initialize storage with file persistence
storage_path = Path("oauth_clients.json")
_storage = get_storage(storage_path)

# JWKS endpoint
@mcp.custom_route("/.well-known/jwks.json", methods=["GET"])
async def jwks_endpoint_route(request):
    _, public_key_pem = get_or_create_keypair()
    jwk = public_key_to_jwk(public_key_pem, kid=DEFAULT_KID)
    return add_cors_headers(JSONResponse({"keys": [jwk]}))

# OAuth Protected Resource Metadata (RFC 9728) - Primary MCP discovery endpoint
@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def protected_resource_metadata_route(request):
    return add_cors_headers(JSONResponse({
        "resource": "http://localhost:8000",
        "authorization_servers": ["http://localhost:8000"]
    }))

# OAuth Authorization Server Metadata
@mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def auth_server_metadata_route(request):
    return add_cors_headers(JSONResponse({
        "issuer": "http://localhost:8000",
        "authorization_endpoint": "http://localhost:8000/oauth/authorize",
        "token_endpoint": "http://localhost:8000/oauth/token",
        "registration_endpoint": "http://localhost:8000/register",
        "jwks_uri": "http://localhost:8000/.well-known/jwks.json",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": ["mcp:tools"],
        "code_challenge_methods_supported": ["S256", "plain"]
    }))

# Authorization endpoint for Authorization Code flow
@mcp.custom_route("/oauth/authorize", methods=["GET", "POST"])
async def authorize_endpoint_route(request):
    from starlette.responses import RedirectResponse, HTMLResponse
    from urllib.parse import quote

    # Extract authorization request parameters
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    state = request.query_params.get("state")
    code_challenge = request.query_params.get("code_challenge")
    code_challenge_method = request.query_params.get("code_challenge_method", "plain")
    scope = request.query_params.get("scope", "mcp:tools")

    if not client_id or not redirect_uri:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_request", "error_description": "Missing required parameters"}
        )

    # Validate client exists
    storage = get_storage()
    client = storage.get_client(client_id)
    if not client:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_client", "error_description": f"Client {client_id} not found"}
        )

    # Validate redirect_uri
    if redirect_uri not in client.redirect_uris:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_request", "error_description": "Invalid redirect_uri"}
        )

    # If POST request (user clicked authorize button), generate code and redirect
    if request.method == "POST":
        # Generate authorization code
        auth_code = secrets.token_urlsafe(32)

        # Store the authorization code with associated data
        storage.store_authorization_code(
            code=auth_code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            scope=scope
        )

        # Redirect back to client with authorization code
        redirect_url = f"{redirect_uri}?code={auth_code}"
        if state:
            redirect_url += f"&state={state}"

        return RedirectResponse(url=redirect_url, status_code=302)

    # GET request - show authorization page
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authorize Application</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .auth-container {{
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                max-width: 400px;
                width: 100%;
            }}
            h1 {{
                margin-top: 0;
                color: #333;
                font-size: 24px;
            }}
            .info {{
                background: #f5f5f5;
                padding: 15px;
                border-radius: 6px;
                margin: 20px 0;
            }}
            .info-row {{
                margin: 8px 0;
                font-size: 14px;
                color: #666;
            }}
            .info-label {{
                font-weight: 600;
                color: #333;
            }}
            .scope {{
                background: #667eea;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                display: inline-block;
                margin: 4px 0;
            }}
            button {{
                width: 100%;
                padding: 14px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.2s;
            }}
            button:hover {{
                background: #5568d3;
            }}
            .security-note {{
                margin-top: 20px;
                padding: 12px;
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                border-radius: 4px;
                font-size: 13px;
                color: #856404;
            }}
        </style>
    </head>
    <body>
        <div class="auth-container">
            <h1>🔐 Authorization Request</h1>
            <div class="info">
                <div class="info-row">
                    <span class="info-label">Application:</span> {client.client_name}
                </div>
                <div class="info-row">
                    <span class="info-label">Client ID:</span> {client_id[:20]}...
                </div>
                <div class="info-row">
                    <span class="info-label">Requested Scope:</span><br>
                    <span class="scope">{scope}</span>
                </div>
            </div>
            <form method="POST" action="/oauth/authorize?{request.url.query}">
                <button type="submit">Authorize Access</button>
            </form>
            <div class="security-note">
                This application will be able to access your MCP server tools.
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Client Registration endpoint
@mcp.custom_route("/register", methods=["POST"])
async def register_endpoint_route(request):
    # Parse JSON body
    body = await request.json()
    req_data = ClientRegistrationRequest(**body)

    client_id = str(uuid.uuid4())
    client_secret = secrets.token_urlsafe(32)
    registration_access_token = secrets.token_urlsafe(32)
    redirect_uris = req_data.redirect_uris or []
    grant_types = req_data.grant_types or ["client_credentials"]

    storage = get_storage()
    client = storage.create_client(
        client_id=client_id,
        client_secret=client_secret,
        client_name=req_data.client_name,
        redirect_uris=redirect_uris,
        grant_types=grant_types,
        registration_access_token=registration_access_token
    )

    response_data = ClientRegistrationResponse(
        client_id=client.client_id,
        client_secret=client.client_secret,
        client_name=client.client_name,
        redirect_uris=client.redirect_uris,
        grant_types=client.grant_types,
        token_endpoint_auth_method="client_secret_post",
        registration_access_token=registration_access_token,
        registration_client_uri=f"http://localhost:8000/register/{client_id}"
    ).model_dump()
    return add_cors_headers(JSONResponse(response_data))

# Token endpoint
@mcp.custom_route("/oauth/token", methods=["POST"])
async def token_endpoint_route(request):
    import hashlib
    import base64

    # Parse form data
    form = await request.form()
    grant_type = form.get("grant_type")
    client_id = form.get("client_id")
    client_secret = form.get("client_secret")

    storage = get_storage()

    # Validate grant type
    if grant_type == "client_credentials":
        # Client Credentials flow
        scope = form.get("scope", "mcp:tools")

        if not storage.validate_credentials(client_id, client_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_client"}
            )

    elif grant_type == "authorization_code":
        # Authorization Code flow
        code = form.get("code")
        redirect_uri = form.get("redirect_uri")
        code_verifier = form.get("code_verifier")

        if not code or not redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_request", "error_description": "Missing required parameters"}
            )

        # Validate credentials
        if not storage.validate_credentials(client_id, client_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_client"}
            )

        # Get and validate authorization code
        auth_code = storage.get_authorization_code(code)
        if not auth_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_grant", "error_description": "Invalid or expired authorization code"}
            )

        # Validate client_id matches
        if auth_code.client_id != client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_grant"}
            )

        # Validate redirect_uri matches
        if auth_code.redirect_uri != redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_grant"}
            )

        # Validate PKCE if code_challenge was used
        if auth_code.code_challenge:
            if not code_verifier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "invalid_request", "error_description": "code_verifier required"}
                )

            # Verify code challenge
            if auth_code.code_challenge_method == "S256":
                computed_challenge = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                ).decode().rstrip("=")
            else:  # plain
                computed_challenge = code_verifier

            if computed_challenge != auth_code.code_challenge:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "invalid_grant", "error_description": "Invalid code_verifier"}
                )

        # Mark code as used
        storage.mark_code_as_used(code)
        scope = auth_code.scope

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "unsupported_grant_type"}
        )

    # Generate access token
    private_key_pem, _ = get_or_create_keypair()
    access_token = create_access_token(
        client_id=client_id,
        issuer="http://localhost:8000",
        audience="mcp-greeting-server",
        private_key_pem=private_key_pem,
        kid=DEFAULT_KID,
        expires_delta=timedelta(hours=1),
        scope=scope
    )

    response_data = TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=3600,
        scope=scope
    ).model_dump()
    return add_cors_headers(JSONResponse(response_data))

def main() -> None:
    """Entry point to start the combined OAuth + MCP server."""
    import sys
    import os

    # Check for explicit STDIO mode via environment variable
    use_stdio = os.getenv("MCP_TRANSPORT") == "stdio"

    if use_stdio:
        # Running via inspector or piped input, use STDIO (no OAuth)
        logger.warning("Running via STDIO transport - OAuth authentication disabled")
        logger.warning("For OAuth testing, run: uv run main.py")
        # Create a simple MCP server without auth for STDIO
        from mcp.server.fastmcp import FastMCP
        simple_mcp = FastMCP("hello-server")

        @simple_mcp.tool()
        def say_hello(name: str) -> str:
            """Return a personalized greeting."""
            return f"Hello, {name}! (STDIO mode - no auth)"

        simple_mcp.run(transport="stdio")
    else:
        # Default: use SSE transport with OAuth
        logger.info("Starting OAuth + MCP server on http://localhost:8000")
        mcp.run(transport="sse")

if __name__ == "__main__":
    main()