# Greeting MCP Server with OAuth 2.0 DCR

A simple MCP server implementing OAuth 2.0 Dynamic Client Registration with a single greeting tool.

## Features

- **OAuth 2.0 Dynamic Client Registration** (RFC 7591) - automatic client onboarding
- **Authorization Code Flow** with PKCE (S256 and plain)
- **RS256 JWT tokens** with 1-hour expiration
- **JWKS endpoint** for public key discovery
- **MCP Tool**: `say_hello(name)` - returns a personalized greeting message
- **Thread-safe client storage** persisted to `oauth_clients.json`

## Running the Server

```bash
uv run main.py
```

Server starts on `http://localhost:8000` with both OAuth and MCP endpoints.

## MCP Tool

**`say_hello(name: string)`**

Returns a greeting message for the provided name.

Example:
```json
{
  "name": "Alice"
}
// Returns: "Hello, Alice! Welcome to the MCP server with OAuth 2.0 authentication."
```

## OAuth Endpoints

- `GET /.well-known/oauth-protected-resource` - MCP discovery (RFC 9728)
- `GET /.well-known/oauth-authorization-server` - OAuth metadata
- `GET /.well-known/jwks.json` - Public keys for JWT verification
- `POST /register` - Dynamic Client Registration
- `GET/POST /oauth/authorize` - Authorization endpoint (with PKCE)
- `POST /oauth/token` - Token issuance (supports `authorization_code` and `client_credentials`)

## Authentication Flow

1. Client discovers OAuth server via `/.well-known/oauth-protected-resource`
2. Client registers via `POST /register` to get credentials
3. Client obtains authorization code via `/oauth/authorize` (optional, for user flows)
4. Client exchanges code for JWT access token via `POST /oauth/token`
5. Client calls MCP tools with `Authorization: Bearer <token>` header

## File Structure

```
greeting_mcp_server/
├── main.py              # Server implementation
├── pyproject.toml       # Dependencies
├── .env                 # Configuration
├── oauth_clients.json   # Registered clients (auto-created)
├── keys/                # RSA keypair for JWT signing
│   ├── private_key.pem 
│   └── public_key.pem
└── oauth/               # OAuth implementation modules
    ├── jwt_utils.py     # JWT creation and key management
    ├── storage.py       # Thread-safe client storage
    └── schemas/         # Pydantic models
```

## Dependencies

See [pyproject.toml](pyproject.toml) for the full list. Key dependencies:
- `fastmcp` - MCP server framework
- `pyjwt[crypto]` - JWT token handling
- `cryptography` - RSA key generation
- `fastapi` + `uvicorn` - Web server
