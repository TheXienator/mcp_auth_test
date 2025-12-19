"""MCP server discovery helpers."""

import httpx
from typing import Any


async def discover_mcp_server(server_url: str, timeout: float = 30.0) -> dict[str, Any]:
    """
    Discover MCP server's OAuth protected resource metadata.

    Args:
        server_url: Base URL of MCP server (e.g., http://localhost:8000)
        timeout: HTTP request timeout in seconds

    Returns:
        Protected resource metadata with authorization_servers array

    Raises:
        httpx.HTTPError: If discovery fails
    """
    url = f"{server_url.rstrip('/')}/.well-known/oauth-protected-resource"

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def get_sse_endpoint(server_url: str) -> str:
    """
    Get SSE endpoint URL for MCP server.

    Args:
        server_url: Base URL of MCP server

    Returns:
        SSE endpoint URL (typically server_url/sse)
    """
    # Return URL with /sse endpoint
    return f"{server_url.rstrip('/')}/sse"
