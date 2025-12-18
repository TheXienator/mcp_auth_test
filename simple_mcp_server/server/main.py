from fastapi import FastAPI, Depends, HTTPException, status, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from config import get_settings
from server.oauth.token import create_access_token
from server.oauth.dependencies import validate_token
from server.oauth.schemas import TokenResponse
from server.well_known.endpoints import router as well_known_router
from server.mcp.tools import TOOLS
from pydantic import BaseModel

settings = get_settings()
app = FastAPI(title="MCP OAuth Text Server")

# Include well-known endpoints
app.include_router(well_known_router)


# Login UI endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to login page"""
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve login page with password form"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCP OAuth Server - Login</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .login-container {
                background: white;
                padding: 2.5rem;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 400px;
            }
            h1 {
                margin: 0 0 0.5rem 0;
                color: #333;
                font-size: 1.8rem;
            }
            .subtitle {
                color: #666;
                margin: 0 0 2rem 0;
                font-size: 0.95rem;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: #333;
                font-weight: 500;
            }
            input[type="password"] {
                width: 100%;
                padding: 0.75rem;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 1rem;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            input[type="password"]:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                width: 100%;
                padding: 0.875rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            button:active {
                transform: translateY(0);
            }
            .error {
                color: #e53e3e;
                background: #fff5f5;
                padding: 0.75rem;
                border-radius: 6px;
                margin-bottom: 1rem;
                display: none;
                border-left: 4px solid #e53e3e;
            }
            .success {
                color: #38a169;
                background: #f0fff4;
                padding: 0.75rem;
                border-radius: 6px;
                margin-bottom: 1rem;
                border-left: 4px solid #38a169;
            }
            .token-container {
                display: none;
            }
            .token-box {
                background: #f7fafc;
                padding: 1rem;
                border-radius: 6px;
                margin-top: 1rem;
                word-break: break-all;
                font-family: monospace;
                font-size: 0.85rem;
                border: 1px solid #e0e0e0;
            }
            .copy-btn {
                margin-top: 0.75rem;
                background: #48bb78;
            }
            .copy-btn:hover {
                background: #38a169;
            }
            .info {
                margin-top: 1.5rem;
                padding: 1rem;
                background: #ebf8ff;
                border-radius: 6px;
                font-size: 0.9rem;
                color: #2c5282;
                border-left: 4px solid #4299e1;
            }
            .info strong {
                display: block;
                margin-bottom: 0.5rem;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1>MCP OAuth Server</h1>
            <p class="subtitle">Enter password to get access token</p>

            <div id="errorMessage" class="error"></div>

            <form id="loginForm">
                <div class="form-group">
                    <label for="password">Password</label>
                    <input
                        type="password"
                        id="password"
                        name="password"
                        placeholder="Enter password"
                        required
                        autofocus
                    >
                </div>
                <button type="submit">Get Access Token</button>
            </form>

            <div id="tokenContainer" class="token-container">
                <div class="success">
                    ✓ Token generated successfully!
                </div>
                <strong>Your Access Token:</strong>
                <div id="tokenBox" class="token-box"></div>
                <button onclick="copyToken()" class="copy-btn">Copy Token</button>
                <button onclick="resetForm()" style="margin-top: 0.5rem; background: #718096;">Get New Token</button>
            </div>

            <div class="info">
                <strong>Test Password:</strong>
                For testing, use password: <code>placeholder</code>
            </div>
        </div>

        <script>
            const form = document.getElementById('loginForm');
            const errorMessage = document.getElementById('errorMessage');
            const tokenContainer = document.getElementById('tokenContainer');
            const tokenBox = document.getElementById('tokenBox');
            let currentToken = '';

            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                errorMessage.style.display = 'none';

                const password = document.getElementById('password').value;

                try {
                    const response = await fetch('/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: `password=${encodeURIComponent(password)}`
                    });

                    const data = await response.json();

                    if (response.ok) {
                        currentToken = data.access_token;
                        tokenBox.textContent = currentToken;
                        form.style.display = 'none';
                        tokenContainer.style.display = 'block';
                    } else {
                        errorMessage.textContent = data.detail || 'Invalid password';
                        errorMessage.style.display = 'block';
                    }
                } catch (error) {
                    errorMessage.textContent = 'Error connecting to server';
                    errorMessage.style.display = 'block';
                }
            });

            function copyToken() {
                navigator.clipboard.writeText(currentToken).then(() => {
                    const btn = event.target;
                    const originalText = btn.textContent;
                    btn.textContent = '✓ Copied!';
                    setTimeout(() => {
                        btn.textContent = originalText;
                    }, 2000);
                });
            }

            function resetForm() {
                form.style.display = 'block';
                tokenContainer.style.display = 'none';
                document.getElementById('password').value = '';
                errorMessage.style.display = 'none';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/login")
async def login_submit(password: str = Form(...)):
    """Handle password login and return access token"""
    # Check if password matches
    if password != settings.CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )

    # Generate access token
    access_token, expires_in = create_access_token("web_user")

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in
    )


# OAuth token endpoint
@app.post("/oauth/token", response_model=TokenResponse)
async def token_endpoint(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    """OAuth 2.0 Client Credentials token endpoint"""

    # Validate grant type
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported grant type"
        )

    # Validate credentials
    if client_id != settings.CLIENT_ID or client_secret != settings.CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials"
        )

    # Create token
    access_token, expires_in = create_access_token(client_id)

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in
    )


# MCP tool discovery endpoint
@app.get("/mcp/v1/tools/list")
async def list_tools(token_claims: dict = Depends(validate_token)):
    """List available MCP tools (protected)"""
    return {
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            }
            for tool in TOOLS.values()
        ]
    }


# MCP tool call endpoint
class ToolCallRequest(BaseModel):
    name: str
    arguments: dict = {}


@app.post("/mcp/v1/tools/call")
async def call_tool(
    request: ToolCallRequest,
    token_claims: dict = Depends(validate_token)
):
    """Call an MCP tool (protected)"""

    tool = TOOLS.get(request.name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{request.name}' not found"
        )

    try:
        result = tool["handler"](**request.arguments)
        return {
            "content": [
                {
                    "type": "text",
                    "text": result
                }
            ]
        }
    except TypeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid arguments: {str(e)}"
        )


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
