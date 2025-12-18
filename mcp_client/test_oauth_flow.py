"""
Test script for OAuth discovery flow

This script tests the full OAuth discovery flow programmatically without manual interaction.
"""

import asyncio
import httpx
from client.mcp_client import MCPClient
from client.mock_claude import MockClaude


async def get_token_programmatically(server_uri: str) -> str:
    """Get access token via OAuth client credentials grant"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{server_uri}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "client_placeholder",
                "client_secret": "placeholder",
            }
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def test_oauth_discovery():
    """Test the full OAuth discovery flow"""
    server_uri = "http://localhost:8000"

    print("=" * 60)
    print("Testing MCP Client OAuth Discovery Flow")
    print("=" * 60)
    print()

    # Step 1: Create MCP client
    print("Step 1: Creating MCP client...")
    mcp_client = MCPClient(server_uri)
    print("✓ MCP client created")
    print()

    # Step 2: Test unauthenticated call (should fail)
    print("Step 2: Testing unauthenticated tool list (should fail)...")
    try:
        await mcp_client.list_tools(access_token=None)
        print("✗ ERROR: Should have failed without auth!")
        return False
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            print(f"✓ Correctly received {e.response.status_code} (authentication required)")
            www_auth = e.response.headers.get('WWW-Authenticate')
            if www_auth:
                print(f"  WWW-Authenticate header: {www_auth}")
        else:
            print(f"✗ ERROR: Unexpected status code {e.response.status_code}")
            return False
    print()

    # Step 3: Perform OAuth discovery
    print("Step 3: Performing OAuth discovery...")
    try:
        login_url = await mcp_client.perform_oauth_discovery()
        print(f"✓ Discovery successful")
        print(f"  Login URL: {login_url}")
    except Exception as e:
        print(f"✗ ERROR during discovery: {e}")
        return False
    print()

    # Step 4: Get access token
    print("Step 4: Getting access token...")
    try:
        access_token = await get_token_programmatically(server_uri)
        mcp_client.set_access_token(access_token)
        print(f"✓ Token obtained: {access_token[:20]}...")
    except Exception as e:
        print(f"✗ ERROR getting token: {e}")
        return False
    print()

    # Step 5: List tools with token
    print("Step 5: Listing tools with authentication...")
    try:
        tools = await mcp_client.list_tools(access_token)
        print(f"✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
    except Exception as e:
        print(f"✗ ERROR listing tools: {e}")
        return False
    print()

    # Step 6: Test Mock Claude intent detection
    print("Step 6: Testing Mock Claude intent detection...")
    mock_claude = MockClaude(tools)

    test_messages = [
        "tell me a joke",
        "save joke: Why did the chicken cross the road? To get to the other side!",
        "show me the text",
        "edit text to: Hello World",
    ]

    for message in test_messages:
        analysis = mock_claude.analyze_intent(message)
        print(f"  Message: '{message}'")
        print(f"    → Tool: {analysis['tool_name']}")
        print(f"    → Args: {analysis['arguments']}")
        print()

    # Step 7: Call a tool (get_joke)
    print("Step 7: Calling get_joke tool...")
    try:
        result = await mcp_client.call_tool("get_joke", {}, access_token)
        joke = result.get('content', [{}])[0].get('text', 'No joke returned')
        print(f"✓ Joke received:")
        print(f"  {joke}")
    except Exception as e:
        print(f"✗ ERROR calling tool: {e}")
        return False
    print()

    # Step 8: Call save_joke tool
    print("Step 8: Calling save_joke tool...")
    try:
        result = await mcp_client.call_tool(
            "save_joke",
            {
                "joke": "What do you call a fake noodle? An impasta!",
                "category": "puns"
            },
            access_token
        )
        response = result.get('content', [{}])[0].get('text', 'No response')
        print(f"✓ Save result:")
        print(f"  {response}")
    except Exception as e:
        print(f"✗ ERROR calling tool: {e}")
        return False
    print()

    print("=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_oauth_discovery())
    exit(0 if success else 1)
