# Dynamic MCP Client

A web-based MCP (Model Context Protocol) client with OAuth 2.1 Dynamic Client Registration (DCR) support.

## Features

- **Dynamic Client Registration** - Automatically registers with MCP servers supporting DCR
- **OAuth 2.1 Authorization** - Full PKCE-enabled authorization code flow
- **SSE Transport** - Connects to MCP servers via Server-Sent Events
- **Web Interface** - Browser-based UI for managing servers
- **Persistent Storage** - Saves server configurations and tokens locally
- **Secure** - PKCE, state validation, and automatic OAuth discovery

## Installation

```bash
cd dynamic_mcp_client
uv sync
```

## Usage

Start the web server:

```bash
uv run main.py
```

Open `http://localhost:3000` in your browser.

### Adding a Server

1. Click "Add Server"
2. Enter server name and URL (e.g., `http://localhost:8000`)
3. Click "Add Server" - automatically performs DCR and saves the server
4. Back on the home page, click "Connect" to authorize via OAuth
5. Complete authorization in the browser popup

### Testing a Server Connection

Click "Test Connection" on any authorized server to verify the connection and list available tools.

## Architecture

```
dynamic_mcp_client/
├── oauth/               # OAuth 2.1 client implementation
│   ├── client.py        # OAuth client (DCR, token exchange)
│   ├── pkce.py          # PKCE generator
│   └── browser.py       # Browser auth flow + callback server
├── mcp_client/          # MCP client implementation
│   ├── client.py        # SSE client with Bearer auth
│   └── discovery.py     # OAuth discovery helpers
├── storage/             # Persistence layer
│   ├── models.py        # Pydantic models
│   └── persistence.py   # JSON file storage
├── web/                 # FastAPI web interface
│   ├── app.py           # Web application
│   └── templates/       # HTML templates
└── main.py              # Entry point
```

## How It Works

### Server Registration Flow

**Step 1: Add Server**
1. User enters server URL
2. Client discovers OAuth metadata from `/.well-known/oauth-authorization-server`
3. Client performs DCR and receives `client_id` and `client_secret`
4. Server configuration saved (without access token)

**Step 2: Connect**
5. User clicks "Connect" button on home page
6. Client generates PKCE pair and opens browser for authorization
7. User approves in browser
8. Client exchanges authorization code for access token
9. Access token saved to storage

**Step 3: Use**
- Click "Test Connection" to verify and list available tools
- Client uses Bearer token for authenticated MCP requests

## Testing

Also provided a `uv run test_automated.py` which goes through the whole flow assuming that the user ran `uv run main.py` on the greeting_mcp_server already.

## Security

- **PKCE (S256)** - Proof Key for Code Exchange prevents authorization code interception
- **State Parameter** - CSRF protection in OAuth flow
- **Secure Storage** - Token file has 0600 permissions (owner read/write only)
- **Token Expiration** - Checks token validity before each connection

## Dependencies

- `mcp[cli]` - MCP Python SDK
- `httpx` - Async HTTP client
- `fastapi` - Web framework
- `pydantic` - Data validation
- `uvicorn` - ASGI server
