# MCP Self-Register Auth

A test implementation of the Model Context Protocol (MCP) [Authorization specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization). This project demonstrates how MCP servers can implement secure authentication flows using OAuth 2.0 Client Credentials grant with self-registration capabilities.

## Overview

This repository is a proof-of-concept testing the MCP authorization specification. It contains:
- **simple_mcp_server**: An MCP server implementation with OAuth 2.0 authentication
- **mcp_client**: A client implementation that demonstrates the OAuth flow and MCP tool usage

## Features

- OAuth 2.0 Client Credentials Grant for secure authentication
- MCP specification compliant (RFC 9728 & RFC 8414)
- Well-known endpoints for service discovery as per [MCP Authorization spec](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- JWT-based token authentication
- File-based persistence
- Full integration tests

## Project Structure

```
├── simple_mcp_server/     # MCP server with OAuth 2.0
│   ├── server/
│   │   ├── main.py        # FastAPI application
│   │   ├── oauth/         # OAuth implementation
│   │   ├── mcp/           # MCP tools
│   │   ├── well_known/    # Discovery endpoints
│   │   └── storage/       # Data persistence
│   └── tests/             # Integration tests
├── mcp_client/            # Client implementation
│   └── client/
│       ├── mcp_client.py  # MCP client
│       └── oauth_manager.py # OAuth flow handler
└── README.md
```

## Quick Start

### Server Setup

1. Navigate to the server directory:
```bash
cd simple_mcp_server
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Configure `.env` file with your settings

4. Start the server:
```bash
python3 -m uvicorn server.main:app --reload --port 8000
```

### Client Usage

1. Navigate to the client directory:
```bash
cd mcp_client
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Configure `.env` file

4. Run the client:
```bash
python3 main.py
```

## Documentation

See [simple_mcp_server/README.md](simple_mcp_server/__pycache__/README.md) for detailed server documentation including:
- API endpoints
- Authentication flow
- Tool usage examples
- Security features
- Testing instructions

## MCP Authorization Specification

This project implements the authorization flow described in the [MCP Authorization specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization), including:
- Resource metadata endpoint (`/.well-known/mcp-resource-metadata.json`)
- Authorization server metadata endpoint (`/.well-known/oauth-authorization-server`)
- Token endpoint with client credentials grant
- Bearer token authentication for protected resources

## License

MIT License
