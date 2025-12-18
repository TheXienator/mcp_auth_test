import httpx
from typing import Dict, List, Optional, Any
from client.oauth_manager import OAuthManager


class MCPClient:
    """MCP protocol client with OAuth support"""

    def __init__(self, server_uri: str):
        self.server_uri = server_uri
        self.oauth_manager = OAuthManager(server_uri)
        self.tools: List[Dict] = []

    async def list_tools(self, access_token: Optional[str] = None) -> List[Dict]:
        """
        List available MCP tools
        Raises httpx.HTTPStatusError if authentication fails
        """
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.server_uri}/mcp/v1/tools/list",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            self.tools = data["tools"]
            return self.tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        access_token: Optional[str] = None
    ) -> Dict:
        """
        Call an MCP tool
        Raises httpx.HTTPStatusError if authentication fails or tool not found
        """
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_uri}/mcp/v1/tools/call",
                headers=headers,
                json={"name": tool_name, "arguments": arguments}
            )
            response.raise_for_status()
            return response.json()

    async def perform_oauth_discovery(self) -> str:
        """
        Perform full OAuth discovery flow
        Returns: Login URL for user to visit
        """
        metadata = await self.oauth_manager.discover_auth_server()
        return self.oauth_manager.get_authorization_url()

    def set_access_token(self, token: str, expires_in: int = 3600):
        """Set access token after user authentication"""
        self.oauth_manager.set_token(token, expires_in)

    def get_access_token(self) -> Optional[str]:
        """Get current valid access token"""
        return self.oauth_manager.get_token()
