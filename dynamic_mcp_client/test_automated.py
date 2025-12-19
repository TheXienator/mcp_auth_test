#!/usr/bin/env python3
"""
Automated end-to-end test of the OAuth DCR flow.
Simulates the browser interaction programmatically.
"""

import asyncio
import httpx
from oauth.client import OAuthClient
from oauth.pkce import generate_pkce_pair
from mcp_client.discovery import get_sse_endpoint
from mcp_client.client import MCPClient
import secrets
from urllib.parse import parse_qs, urlparse


async def simulate_browser_authorization(auth_url: str, client_secret: str) -> tuple[str, str]:
    """
    Simulate what the browser does during OAuth authorization.

    Args:
        auth_url: The authorization URL to visit
        client_secret: Client secret for this test

    Returns:
        Tuple of (authorization_code, state)
    """
    print("\n  🌐 Simulating browser authorization...")

    # Parse the auth URL to extract parameters
    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)

    state = params['state'][0]
    print(f"  📋 State parameter: {state}")

    async with httpx.AsyncClient(follow_redirects=False) as client:
        # Step 1: GET the authorization page (what browser does)
        print("  📄 GET authorization page...")
        response = await client.get(auth_url)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "Authorize Application" in response.text, "Auth page not rendered"
        print("  ✓ Authorization page loaded")

        # Step 2: POST to approve (simulating clicking "Authorize Access")
        print("  ✅ Simulating 'Authorize Access' click...")
        response = await client.post(
            auth_url,
            data={
                # The form posts back the same parameters
                "client_id": params['client_id'][0],
                "response_type": "code",
                "redirect_uri": params['redirect_uri'][0],
                "state": state,
                "code_challenge": params['code_challenge'][0],
                "code_challenge_method": "S256",
                "scope": params.get('scope', [''])[0]
            }
        )

        # Should get a 302 redirect
        assert response.status_code == 302, f"Expected 302 redirect, got {response.status_code}"
        print("  ✓ Got 302 redirect")

        # Extract redirect location
        redirect_url = response.headers['location']
        print(f"  📍 Redirect to: {redirect_url[:80]}...")

        # Parse the callback URL to extract the authorization code
        callback_parsed = urlparse(redirect_url)
        callback_params = parse_qs(callback_parsed.query)

        code = callback_params['code'][0]
        returned_state = callback_params['state'][0]

        print(f"  🎫 Authorization code: {code[:40]}...")
        print(f"  ✓ State matches: {state == returned_state}")

        assert state == returned_state, "State mismatch!"

        return code, state


async def test_full_oauth_flow():
    """Test the complete OAuth DCR flow automatically."""

    server_url = "http://localhost:8000"
    print(f"\n{'='*70}")
    print(f"🧪 AUTOMATED OAUTH DCR FLOW TEST")
    print(f"{'='*70}\n")

    oauth_client = OAuthClient(server_url)

    try:
        # Step 1: OAuth Discovery
        print("1️⃣  Discovering OAuth metadata...")
        metadata = await oauth_client.discover_oauth_metadata()
        print(f"   ✓ Found OAuth server: {metadata['issuer']}")
        print(f"   ✓ PKCE support: {metadata['code_challenge_methods_supported']}")

        # Step 2: Dynamic Client Registration
        print("\n2️⃣  Performing Dynamic Client Registration...")
        redirect_uri = "http://localhost:8080/callback"
        dcr_response = await oauth_client.register_client(
            client_name="Automated Test Client",
            redirect_uri=redirect_uri
        )
        client_id = dcr_response['client_id']
        client_secret = dcr_response['client_secret']
        print(f"   ✓ Client registered")
        print(f"   ✓ Client ID: {client_id}")
        print(f"   ✓ Client Secret: {client_secret[:30]}...")

        # Step 3: Generate PKCE
        print("\n3️⃣  Generating PKCE parameters...")
        code_verifier, code_challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(16)
        print(f"   ✓ Code verifier: {code_verifier[:40]}...")
        print(f"   ✓ Code challenge: {code_challenge}")
        print(f"   ✓ State: {state}")

        # Step 4: Build authorization URL
        print("\n4️⃣  Building authorization URL...")
        auth_url = oauth_client.build_authorization_url(
            authorization_endpoint=metadata["authorization_endpoint"],
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge
        )
        print(f"   ✓ URL: {auth_url[:100]}...")

        # Step 5: Simulate browser authorization
        print("\n5️⃣  Simulating browser authorization flow...")
        code, returned_state = await simulate_browser_authorization(auth_url, client_secret)
        print(f"   ✓ Authorization code obtained: {code[:40]}...")

        # Step 6: Exchange code for token
        print("\n6️⃣  Exchanging authorization code for access token...")
        token_response = await oauth_client.exchange_code_for_token(
            token_endpoint=metadata["token_endpoint"],
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )

        access_token = token_response['access_token']
        print(f"   ✓ Access token received: {access_token[:50]}...")
        print(f"   ✓ Token type: {token_response['token_type']}")
        print(f"   ✓ Expires in: {token_response['expires_in']} seconds")

        # Step 7: Test MCP connection
        print("\n7️⃣  Testing MCP connection with Bearer token...")
        sse_endpoint = await get_sse_endpoint(server_url)
        print(f"   ✓ SSE endpoint: {sse_endpoint}")

        mcp_client = MCPClient(sse_endpoint, access_token)
        init_result = await mcp_client.connect()
        server_name = init_result.serverInfo.name if hasattr(init_result, 'serverInfo') and hasattr(init_result.serverInfo, 'name') else 'Unknown'
        print(f"   ✓ Connected to MCP server: {server_name}")

        tools = await mcp_client.list_tools()
        print(f"   ✓ Found {len(tools)} tool(s):")
        for tool in tools:
            tool_name = tool.name if hasattr(tool, 'name') else 'Unknown'
            tool_desc = tool.description if hasattr(tool, 'description') else 'No description'
            print(f"      - {tool_name}: {tool_desc}")

        # Step 8: Test calling a tool
        if tools:
            print(f"\n8️⃣  Testing tool invocation...")
            test_tool = tools[0]
            tool_name = test_tool.name if hasattr(test_tool, 'name') else 'unknown'
            print(f"   🔧 Calling tool: {tool_name}")

            # For say_hello tool, pass a name argument
            result = await mcp_client.call_tool(tool_name, {"name": "Automated Test"})
            # Result is also a Pydantic model
            if hasattr(result, 'content'):
                print(f"   ✓ Tool result: {result.content}")
            else:
                print(f"   ✓ Tool result: {result}")

        await mcp_client.disconnect()

        # Success!
        print(f"\n{'='*70}")
        print(f"✅ ALL TESTS PASSED!")
        print(f"{'='*70}\n")

        print("📊 Test Summary:")
        print("  ✓ OAuth metadata discovery")
        print("  ✓ Dynamic Client Registration (DCR)")
        print("  ✓ PKCE parameter generation")
        print("  ✓ Authorization URL construction")
        print("  ✓ Browser authorization flow (simulated)")
        print("  ✓ Authorization code exchange")
        print("  ✓ Access token retrieval")
        print("  ✓ MCP SSE connection with Bearer auth")
        print("  ✓ MCP tool listing")
        print("  ✓ MCP tool invocation")
        print("\n🎉 OAuth DCR implementation is working correctly!\n")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await oauth_client.close()


if __name__ == "__main__":
    success = asyncio.run(test_full_oauth_flow())
    exit(0 if success else 1)
