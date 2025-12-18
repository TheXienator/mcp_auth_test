import asyncio
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import print as rprint
from rich.markdown import Markdown
from client.mcp_client import MCPClient
from client.mock_claude import MockClaude
from config import get_settings
import httpx


class MCPClientCLI:
    """Interactive CLI for MCP client with OAuth discovery"""

    def __init__(self):
        self.settings = get_settings()
        self.console = Console()
        self.mcp_client = MCPClient(self.settings.MCP_SERVER_URI)
        self.mock_claude: Optional[MockClaude] = None
        self.authenticated = False

    def display_welcome(self):
        """Display welcome banner"""
        welcome_panel = Panel(
            "[bold cyan]MCP Client with OAuth Discovery[/bold cyan]\n"
            "Demonstrating OAuth 2.0 discovery flow with mocked Claude\n\n"
            f"Server: {self.settings.MCP_SERVER_URI}",
            title="🤖 Welcome",
            border_style="cyan"
        )
        self.console.print(welcome_panel)
        self.console.print()

    async def perform_oauth_flow(self):
        """Execute full OAuth discovery flow with step-by-step display"""
        flow_panel = Panel(
            "[bold yellow]Starting OAuth Discovery Flow[/bold yellow]\n"
            "Following the MCP specification for OAuth 2.0 discovery...",
            title="🔐 Authentication Required",
            border_style="yellow"
        )
        self.console.print(flow_panel)
        self.console.print()

        try:
            # Step 1: Discovery
            self.console.print("[bold]Step 1:[/bold] Discovering OAuth endpoints...")
            login_url = await self.mcp_client.perform_oauth_discovery()
            self.console.print("[green]✓[/green] Discovery complete")
            self.console.print()

            # Step 2: Display login URL
            auth_panel = Panel(
                f"[bold]Please visit this URL to authenticate:[/bold]\n"
                f"[link]{login_url}[/link]\n\n"
                f"[dim]Use password:[/dim] [bold]'placeholder'[/bold]",
                title="🌐 Step 2: User Authentication",
                border_style="blue"
            )
            self.console.print(auth_panel)
            self.console.print()

            # Step 3: Get token from user
            access_token = Prompt.ask(
                "[bold cyan]Paste your access token here[/bold cyan]",
                console=self.console
            )

            # Step 4: Store token
            self.mcp_client.set_access_token(access_token)
            self.console.print("[green]✓[/green] Authentication successful!")
            self.console.print()

            # Step 5: List available tools
            tools = await self.mcp_client.list_tools(access_token)
            tool_names = [tool['name'] for tool in tools]
            self.console.print(
                f"[green]✓[/green] Found {len(tools)} tools: {tool_names}"
            )
            self.console.print()

            # Initialize Mock Claude with available tools
            self.mock_claude = MockClaude(tools)
            self.authenticated = True

        except httpx.HTTPStatusError as e:
            error_panel = Panel(
                f"[bold red]Authentication failed:[/bold red]\n"
                f"Status: {e.response.status_code}\n"
                f"Response: {e.response.text}",
                title="❌ Error",
                border_style="red"
            )
            self.console.print(error_panel)
            return False
        except Exception as e:
            error_panel = Panel(
                f"[bold red]Unexpected error:[/bold red]\n{str(e)}",
                title="❌ Error",
                border_style="red"
            )
            self.console.print(error_panel)
            return False

        return True

    async def attempt_unauthenticated_call(self, user_message: str) -> bool:
        """
        Try to call tool without authentication to demonstrate 401 response
        Returns True if auth is needed, False if call succeeded
        """
        self.console.print(
            "[dim]Attempting to call MCP tool without authentication...[/dim]"
        )

        try:
            # Try to list tools without token
            await self.mcp_client.list_tools(access_token=None)
            return False  # Succeeded without auth
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                self.console.print(
                    f"[yellow]Authentication required (HTTP {e.response.status_code})[/yellow]"
                )
                self.console.print()
                return True  # Auth needed
            else:
                raise  # Other error, re-raise

    async def handle_user_message(self, user_message: str):
        """Process user message and execute appropriate tool"""
        # If not authenticated, try unauthenticated call first to demo flow
        if not self.authenticated:
            needs_auth = await self.attempt_unauthenticated_call(user_message)
            if needs_auth:
                success = await self.perform_oauth_flow()
                if not success:
                    return

        # At this point we should be authenticated
        if not self.authenticated or not self.mock_claude:
            self.console.print("[red]Error: Not authenticated[/red]")
            return

        # Mock Claude analyzes intent
        analysis = self.mock_claude.analyze_intent(user_message)

        # Check if this is a message response instead of a tool call
        if analysis.get('tool_name') is None and 'message' in analysis:
            # Display Claude's analysis
            analysis_panel = Panel(
                f"[bold]Response Type:[/bold] Message\n\n"
                f"[bold]Reasoning:[/bold]\n{analysis['reasoning']}",
                title="🧠 Mock Claude's Analysis",
                border_style="magenta"
            )
            self.console.print(analysis_panel)
            self.console.print()

            # Display the message response
            response_panel = Panel(
                analysis['message'],
                title="📨 Response",
                border_style="green"
            )
            self.console.print(response_panel)
            self.console.print()
            return

        # Display Claude's analysis
        analysis_panel = Panel(
            f"[bold]Tool Selected:[/bold] {analysis['tool_name']}\n"
            f"[bold]Arguments:[/bold] {analysis['arguments']}\n\n"
            f"[bold]Reasoning:[/bold]\n{analysis['reasoning']}",
            title="🧠 Mock Claude's Analysis",
            border_style="magenta"
        )
        self.console.print(analysis_panel)
        self.console.print()

        # Call the tool
        try:
            access_token = self.mcp_client.get_access_token()
            if not access_token:
                self.console.print("[yellow]Token expired, re-authenticating...[/yellow]")
                self.authenticated = False
                await self.handle_user_message(user_message)  # Retry
                return

            result = await self.mcp_client.call_tool(
                analysis['tool_name'],
                analysis['arguments'],
                access_token
            )

            # Display result
            response_content = result.get('content', [{}])[0].get('text', 'No response')
            response_panel = Panel(
                response_content,
                title="📨 Response",
                border_style="green"
            )
            self.console.print(response_panel)
            self.console.print()

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                self.console.print("[yellow]Token expired, re-authenticating...[/yellow]")
                self.authenticated = False
                await self.handle_user_message(user_message)  # Retry
            else:
                error_panel = Panel(
                    f"[bold red]Tool call failed:[/bold red]\n"
                    f"Status: {e.response.status_code}\n"
                    f"Response: {e.response.text}",
                    title="❌ Error",
                    border_style="red"
                )
                self.console.print(error_panel)
        except Exception as e:
            error_panel = Panel(
                f"[bold red]Unexpected error:[/bold red]\n{str(e)}",
                title="❌ Error",
                border_style="red"
            )
            self.console.print(error_panel)

    async def run(self):
        """Main CLI loop"""
        self.display_welcome()

        self.console.print(
            "[dim]Type 'quit' or 'exit' to end the session[/dim]\n"
        )

        while True:
            try:
                user_input = Prompt.ask(
                    "[bold green]You[/bold green]",
                    console=self.console
                )

                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.console.print("\n[cyan]Goodbye! 👋[/cyan]")
                    break

                if not user_input.strip():
                    continue

                self.console.print()
                await self.handle_user_message(user_input)

            except KeyboardInterrupt:
                self.console.print("\n\n[cyan]Goodbye! 👋[/cyan]")
                break
            except EOFError:
                self.console.print("\n\n[cyan]Goodbye! 👋[/cyan]")
                break


async def main():
    """Entry point for CLI"""
    cli = MCPClientCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
