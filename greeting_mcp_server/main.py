from mcp.server.fastmcp import FastMCP
import logging

# Configure logging to write to stderr instead of stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
# Create the MCP server with a friendly name
mcp = FastMCP("hello-server")

@mcp.tool()
def say_hello(name: str) -> str:
    """Return a personalized greeting.
    Args:
        name: The name of the person to greet.
    Returns:
        A friendly greeting string.
    """
    # Log the call so we can see activity in the inspector's notification pane
    logger.info(f"say_hello called with name={name}")
    return f"Hello, {name}! Welcome to your first MCP server."

def main() -> None:
    """Entry point to start the server via STDIO."""
    # transport='stdio' means the server will communicate over stdin/stdout
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()