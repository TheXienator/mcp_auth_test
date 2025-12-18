import httpx
from typing import Optional, Dict
from datetime import datetime, timedelta


class OAuthManager:
    """Manages OAuth tokens and discovery flow"""

    def __init__(self, server_uri: str):
        self.server_uri = server_uri
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.metadata: Optional[Dict] = None

    async def discover_auth_server(self) -> Dict:
        """
        Fetch OAuth server metadata from well-known endpoints
        Returns authorization server metadata
        """
        async with httpx.AsyncClient() as client:
            # Step 1: Get protected resource metadata
            resource_url = f"{self.server_uri}/.well-known/mcp-resource-metadata.json"
            resource_resp = await client.get(resource_url)
            resource_resp.raise_for_status()
            resource_metadata = resource_resp.json()

            # Step 2: Get authorization server metadata
            auth_server_url = f"{self.server_uri}/.well-known/oauth-authorization-server"
            auth_resp = await client.get(auth_server_url)
            auth_resp.raise_for_status()
            self.metadata = auth_resp.json()

            return self.metadata

    def get_authorization_url(self) -> str:
        """Get the login URL for user authentication"""
        if not self.metadata:
            raise ValueError("Must call discover_auth_server() first")

        # Use custom login_url if available, fallback to authorization_endpoint
        return self.metadata.get("login_url") or self.metadata["authorization_endpoint"]

    def set_token(self, access_token: str, expires_in: int = 3600):
        """Store access token with expiry"""
        self.access_token = access_token
        self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

    def is_token_valid(self) -> bool:
        """Check if current token is valid and not expired"""
        if not self.access_token or not self.token_expiry:
            return False
        return datetime.now() < self.token_expiry

    def get_token(self) -> Optional[str]:
        """Get current valid token or None"""
        if self.is_token_valid():
            return self.access_token
        return None

    def clear_token(self):
        """Clear stored token"""
        self.access_token = None
        self.token_expiry = None
