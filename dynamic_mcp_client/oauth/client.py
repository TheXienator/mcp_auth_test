"""OAuth 2.1 client with Dynamic Client Registration support."""

import httpx
from typing import Any, Optional


class OAuthClient:
    """OAuth client for DCR and token exchange."""

    def __init__(self, server_url: str, timeout: float = 30.0):
        """
        Initialize OAuth client.

        Args:
            server_url: Base URL of the MCP server (e.g., http://localhost:8000)
            timeout: HTTP request timeout in seconds
        """
        self.server_url = server_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def discover_oauth_metadata(self) -> dict[str, Any]:
        """
        Discover OAuth authorization server metadata.

        Tries the provided URL first, then falls back to base URL if it fails.
        This handles cases where server_url might be an SSE endpoint like
        http://localhost:8000/sse instead of the base http://localhost:8000.

        Returns:
            OAuth metadata from /.well-known/oauth-authorization-server

        Raises:
            httpx.HTTPError: If discovery fails on all attempts
        """
        # Try the provided server_url first
        url = f"{self.server_url}/.well-known/oauth-authorization-server"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # If we get 404 or 405, the URL might include a transport path like /sse
            # Try stripping the last path segment
            if e.response.status_code in (404, 405):
                # Extract base URL by removing last path segment
                from urllib.parse import urlparse, urlunparse
                parsed = urlparse(self.server_url)

                # Remove last path segment (e.g., /sse from /sse)
                path_parts = parsed.path.rstrip('/').split('/')
                if len(path_parts) > 1:  # Only if there's a path to remove
                    base_path = '/'.join(path_parts[:-1])
                    base_url = urlunparse((
                        parsed.scheme,
                        parsed.netloc,
                        base_path,
                        '', '', ''
                    ))

                    # Try with base URL
                    fallback_url = f"{base_url}/.well-known/oauth-authorization-server"
                    response = await self.client.get(fallback_url)
                    response.raise_for_status()
                    return response.json()

            # Re-raise if not 404/405 or fallback also failed
            raise

    async def register_client(
        self,
        client_name: str,
        redirect_uri: str,
        grant_types: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Perform Dynamic Client Registration (RFC 7591).

        Args:
            client_name: Human-readable client name
            redirect_uri: OAuth callback URI
            grant_types: Grant types to support (defaults to ['authorization_code'])

        Returns:
            Registration response with client_id, client_secret, etc.

        Raises:
            httpx.HTTPError: If registration fails
        """
        if grant_types is None:
            grant_types = ["authorization_code"]

        metadata = await self.discover_oauth_metadata()
        registration_endpoint = metadata.get("registration_endpoint")

        if not registration_endpoint:
            raise ValueError("Server does not support dynamic client registration")

        request_body = {
            "client_name": client_name,
            "redirect_uris": [redirect_uri],
            "grant_types": grant_types,
            "token_endpoint_auth_method": "client_secret_post"
        }

        response = await self.client.post(registration_endpoint, json=request_body)
        response.raise_for_status()
        return response.json()

    def build_authorization_url(
        self,
        authorization_endpoint: str,
        client_id: str,
        redirect_uri: str,
        state: str,
        code_challenge: str,
        scope: str = "mcp:tools"
    ) -> str:
        """
        Build OAuth authorization URL with PKCE.

        Args:
            authorization_endpoint: Authorization endpoint from metadata
            client_id: Client ID from DCR
            redirect_uri: OAuth callback URI
            state: Random state for CSRF protection
            code_challenge: PKCE code challenge (S256)
            scope: OAuth scope (defaults to 'mcp:tools')

        Returns:
            Complete authorization URL to open in browser
        """
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": scope
        }

        # Use httpx to build URL with query parameters
        url = httpx.URL(authorization_endpoint, params=params)
        return str(url)

    async def exchange_code_for_token(
        self,
        token_endpoint: str,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code_verifier: str
    ) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            token_endpoint: Token endpoint from metadata
            code: Authorization code from callback
            client_id: Client ID
            client_secret: Client secret
            redirect_uri: Same redirect URI used in authorization request
            code_verifier: PKCE code verifier

        Returns:
            Token response with access_token, token_type, expires_in, etc.

        Raises:
            httpx.HTTPError: If token exchange fails
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier
        }

        response = await self.client.post(
            token_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        return response.json()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
