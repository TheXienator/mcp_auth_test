"""
MCP Client with OAuth Discovery

Entry point for the MCP client that demonstrates OAuth 2.0 discovery flow
with a mocked Claude API that intelligently selects tools.

Usage:
    python main.py

Requirements:
    - simple_mcp_server running at http://localhost:8000
    - Install dependencies: pip install -r requirements.txt
"""

import asyncio
from client.cli import main


if __name__ == "__main__":
    asyncio.run(main())
