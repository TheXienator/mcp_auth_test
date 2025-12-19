"""Browser-based OAuth authorization flow with callback server."""

import asyncio
import webbrowser
from typing import Optional

from aiohttp import web


class CallbackServer:
    """Local HTTP server to receive OAuth callbacks."""

    def __init__(self, redirect_uri: str, expected_state: str):
        """
        Initialize callback server.

        Args:
            redirect_uri: OAuth redirect URI (e.g., http://localhost:8080/callback)
            expected_state: Expected state parameter for CSRF protection
        """
        self.redirect_uri = redirect_uri
        self.expected_state = expected_state
        self.code: Optional[str] = None
        self.error: Optional[str] = None
        self.event = asyncio.Event()

    async def callback_handler(self, request: web.Request) -> web.Response:
        """
        Handle OAuth callback request.

        Args:
            request: HTTP request from OAuth server redirect

        Returns:
            HTML response to display in browser
        """
        # Extract code and state from query parameters
        code = request.query.get("code")
        state = request.query.get("state")
        error = request.query.get("error")
        error_description = request.query.get("error_description", "Unknown error")

        # Handle error responses
        if error:
            self.error = f"{error}: {error_description}"
            self.event.set()
            return web.Response(
                text=f"""
                <html>
                <head><title>Authorization Failed</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>❌ Authorization Failed</h1>
                    <p>{self.error}</p>
                    <p>You can close this window and return to the MCP client.</p>
                </body>
                </html>
                """,
                content_type="text/html",
                status=400
            )

        # Validate state parameter (CSRF protection)
        if state != self.expected_state:
            self.error = "Invalid state parameter (possible CSRF attack)"
            self.event.set()
            return web.Response(
                text="""
                <html>
                <head><title>Authorization Failed</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>❌ Security Error</h1>
                    <p>Invalid state parameter. This could be a CSRF attack.</p>
                    <p>You can close this window and try again.</p>
                </body>
                </html>
                """,
                content_type="text/html",
                status=400
            )

        # Extract authorization code
        if not code:
            self.error = "No authorization code received"
            self.event.set()
            return web.Response(
                text="""
                <html>
                <head><title>Authorization Failed</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>❌ Authorization Failed</h1>
                    <p>No authorization code received from server.</p>
                    <p>You can close this window and try again.</p>
                </body>
                </html>
                """,
                content_type="text/html",
                status=400
            )

        # Success!
        self.code = code
        self.event.set()

        return web.Response(
            text="""
            <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #10b981;">✅ Authorization Successful!</h1>
                <p>You can close this window and return to the MCP client.</p>
                <p style="color: #6b7280; font-size: 14px; margin-top: 40px;">
                    The client is now exchanging the authorization code for an access token...
                </p>
            </body>
            </html>
            """,
            content_type="text/html"
        )

    async def start_and_wait(self, port: int = 8080) -> str:
        """
        Start callback server and wait for OAuth redirect.

        Args:
            port: Port to listen on (defaults to 8080)

        Returns:
            Authorization code from callback

        Raises:
            ValueError: If authorization fails or state is invalid
        """
        app = web.Application()
        app.router.add_get("/callback", self.callback_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", port)
        await site.start()

        # Wait for callback
        await self.event.wait()

        # Cleanup
        await runner.cleanup()

        # Check for errors
        if self.error:
            raise ValueError(self.error)

        if not self.code:
            raise ValueError("No authorization code received")

        return self.code


async def open_browser_and_get_code(
    auth_url: str,
    redirect_uri: str,
    expected_state: str,
    port: int = 8080
) -> str:
    """
    Open browser to authorization URL and wait for OAuth callback.

    Args:
        auth_url: Complete authorization URL to open
        redirect_uri: OAuth redirect URI (must match DCR registration)
        expected_state: Expected state parameter for CSRF protection
        port: Local port for callback server (defaults to 8080)

    Returns:
        Authorization code from OAuth callback

    Raises:
        ValueError: If authorization fails
    """
    callback_server = CallbackServer(redirect_uri, expected_state)

    # Start callback server in background
    server_task = asyncio.create_task(callback_server.start_and_wait(port))

    # Give server a moment to start
    await asyncio.sleep(0.5)

    # Open browser
    webbrowser.open(auth_url)

    # Wait for callback
    code = await server_task

    return code
