"""MCP SSE client with OAuth authentication."""

from typing import Any, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPClient:
    """MCP client with SSE transport and OAuth Bearer token auth."""

    def __init__(self, sse_url: str, access_token: str):
        """
        Initialize MCP client.

        Args:
            sse_url: SSE endpoint URL (e.g., http://localhost:8000/sse)
            access_token: OAuth access token for Bearer authentication
        """
        self.sse_url = sse_url
        self.access_token = access_token
        self.session: Optional[ClientSession] = None
        self._sse_context = None
        self._streams = None

    async def connect(self) -> dict[str, Any]:
        """
        Connect to MCP server via SSE with Bearer token.

        Returns:
            Server initialization response

        Raises:
            Exception: If connection or initialization fails
        """
        headers = {"Authorization": f"Bearer {self.access_token}"}

        # Normalize SSE URL - ensure it ends with /sse but doesn't have double /sse
        sse_url = self.sse_url.rstrip('/')
        # Ensure it ends with /sse (but not /sse/sse)
        if sse_url.endswith('/sse/sse'):
            sse_url = sse_url[:-4]  # Remove one '/sse'
        elif not sse_url.endswith('/sse'):
            sse_url = f"{sse_url}/sse"
        
        import logging
        logging.debug(f"Connecting to SSE endpoint: {sse_url}")

        # Open SSE connection
        self._sse_context = sse_client(url=sse_url, headers=headers)
        self._streams = await self._sse_context.__aenter__()

        # Create MCP session
        self.session = ClientSession(
            read_stream=self._streams[0],
            write_stream=self._streams[1]
        )
        await self.session.__aenter__()

        # Initialize
        init_result = await self.session.initialize()
        return init_result

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        List available MCP tools.

        Returns:
            List of tool definitions

        Raises:
            RuntimeError: If not connected
        """
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")

        result = await self.session.list_tools()
        return result.tools if hasattr(result, 'tools') else []

    async def call_tool(self, tool_name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
        """
        Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments (defaults to empty dict)

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If not connected
        """
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")

        if arguments is None:
            arguments = {}

        result = await self.session.call_tool(tool_name, arguments=arguments)
        return result

    async def disconnect(self) -> None:
        """Close MCP session and SSE connection."""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception:
                pass
            self.session = None

        if self._sse_context and self._streams:
            try:
                await self._sse_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._sse_context = None
            self._streams = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


@asynccontextmanager
async def mcp_client_context(sse_url: str, access_token: str):
    """
    Async context manager for MCP client.

    Args:
        sse_url: SSE endpoint URL
        access_token: OAuth access token

    Yields:
        Connected MCPClient instance
    """
    client = MCPClient(sse_url, access_token)
    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()
