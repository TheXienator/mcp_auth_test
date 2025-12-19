# MCP Authentication Test Project

This project explores the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) OAuth 2.0 specification with Dynamic Client Registration (DCR).

## Project Structure

```
mcp_auth_test/
├── greeting_mcp_server/    # MCP server with OAuth 2.0 DCR support
└── dynamic_mcp_client/     # Web-based MCP client with DCR and OAuth flow
```

## What is an MCP Server?

An MCP server provides tools and resources that AI assistants can use through the Model Context Protocol. This project implements an OAuth 2.0 protected MCP server that requires clients to authenticate using Dynamic Client Registration (DCR) before accessing its tools.

## Quick Start

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

### Running the Server

```bash
cd greeting_mcp_server
uv run main.py
```

The server will start on `http://localhost:8000` with OAuth 2.0 authentication and a single MCP tool (`say_hello`).

## Verifying Dynamic Client Registration

You can verify that the server supports DCR in a few ways:

### Method 1: Using MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run main.py
```

1. Click "Connect" and complete the OAuth flow
2. Check `greeting_mcp_server/oauth_clients.json` - you should see a new client entry

### Method 2: Using Claude Desktop

```bash
claude mcp add http://localhost:8000/sse --transport sse
```

Follow the authentication flow, then verify the new client was registered in `oauth_clients.json`.

### Method 3: Using the provided Dynamic MCP Client

```bash
cd dynamic_mcp_client
uv run main.py
```

Open `http://localhost:3000` in your browser. Click "Add Server", enter the server URL (`http://localhost:8000`), then click "Connect" to complete OAuth authorization. The client automatically handles DCR and PKCE.

Verify that a new client was added in `greeting_mcp_server/oauth_clients.json`

## What's Included

The `greeting_mcp_server` implements:
- **OAuth 2.0 Dynamic Client Registration** (RFC 7591)
- **Authorization Code Flow** with PKCE support
- **RS256 JWT** token signing with JWKS discovery
- **MCP Tool**: `say_hello(name)` - returns a personalized greeting
- **Persistent client storage** in `oauth_clients.json`

## Next Steps

See [greeting_mcp_server/README.md](greeting_mcp_server/README.md) for technical details and API documentation.
