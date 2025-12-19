#!/usr/bin/env python3
"""
Test script to exercise OAuth DCR flow with Chrome DevTools inspection.

This script performs the OAuth flow step-by-step so you can observe
each stage in Chrome DevTools.
"""

import asyncio
import secrets
from oauth.client import OAuthClient
from oauth.pkce import generate_pkce_pair
from mcp_client.discovery import get_sse_endpoint


async def test_oauth_flow():
    """Test the complete OAuth DCR flow."""

    server_url = "http://localhost:8000"
    print(f"\n{'='*60}")
    print(f"Testing OAuth DCR Flow with {server_url}")
    print(f"{'='*60}\n")

    # Step 1: Discover OAuth metadata
    print("Step 1: Discovering OAuth metadata...")
    oauth_client = OAuthClient(server_url)

    try:
        metadata = await oauth_client.discover_oauth_metadata()
        print(f"✓ Found OAuth server: {metadata['issuer']}")
        print(f"  - Authorization endpoint: {metadata['authorization_endpoint']}")
        print(f"  - Token endpoint: {metadata['token_endpoint']}")
        print(f"  - Registration endpoint: {metadata['registration_endpoint']}")
        print(f"  - PKCE methods: {metadata['code_challenge_methods_supported']}\n")

        # Step 2: Dynamic Client Registration
        print("Step 2: Performing Dynamic Client Registration (DCR)...")
        redirect_uri = "http://localhost:8080/callback"
        dcr_response = await oauth_client.register_client(
            client_name="Test MCP Client - Chrome DevTools",
            redirect_uri=redirect_uri
        )
        print(f"✓ Client registered successfully!")
        print(f"  - Client ID: {dcr_response['client_id']}")
        print(f"  - Client Secret: {dcr_response['client_secret'][:20]}...")
        print(f"  - Redirect URI: {redirect_uri}\n")

        # Step 3: Generate PKCE parameters
        print("Step 3: Generating PKCE parameters...")
        code_verifier, code_challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(16)
        print(f"✓ PKCE parameters generated:")
        print(f"  - Code Verifier: {code_verifier[:40]}...")
        print(f"  - Code Challenge (S256): {code_challenge}")
        print(f"  - State: {state}\n")

        # Step 4: Build authorization URL
        print("Step 4: Building authorization URL...")
        auth_url = oauth_client.build_authorization_url(
            authorization_endpoint=metadata["authorization_endpoint"],
            client_id=dcr_response["client_id"],
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge
        )

        print(f"\n{'='*60}")
        print("OPEN THIS URL IN CHROME WITH DEVTOOLS:")
        print(f"{'='*60}")
        print(f"\n{auth_url}\n")
        print(f"{'='*60}\n")

        print("Chrome DevTools inspection points:")
        print("1. Network tab: See the authorization request with params:")
        print(f"   - client_id={dcr_response['client_id']}")
        print(f"   - code_challenge={code_challenge}")
        print("   - code_challenge_method=S256")
        print(f"   - state={state}")
        print("   - scope=mcp:tools")
        print("\n2. Elements tab: Inspect the purple gradient auth page")
        print("\n3. Console tab: Check for any JavaScript errors")
        print("\n4. After clicking 'Authorize Access':")
        print("   - Network tab will show redirect to localhost:8080/callback")
        print("   - URL will contain 'code' and 'state' parameters")
        print(f"\n{'='*60}\n")

        # Step 5: Wait for manual authorization
        print("Now:")
        print("1. Open the URL above in Chrome")
        print("2. Open DevTools (Cmd+Option+I on Mac, F12 on Windows/Linux)")
        print("3. Click 'Authorize Access'")
        print("4. Copy the 'code' parameter from the callback URL")
        print("\nPaste the authorization code here: ", end="")

        code = input().strip()

        if not code:
            print("\n❌ No code provided. Exiting.")
            await oauth_client.close()
            return

        # Step 6: Exchange code for token
        print(f"\nStep 5: Exchanging authorization code for access token...")
        token_response = await oauth_client.exchange_code_for_token(
            token_endpoint=metadata["token_endpoint"],
            code=code,
            client_id=dcr_response["client_id"],
            client_secret=dcr_response["client_secret"],
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )

        print(f"✓ Token exchange successful!")
        print(f"  - Access Token: {token_response['access_token'][:50]}...")
        print(f"  - Token Type: {token_response['token_type']}")
        print(f"  - Expires In: {token_response['expires_in']} seconds")
        print(f"  - Scope: {token_response.get('scope', 'mcp:tools')}\n")

        # Step 7: Test MCP connection
        print("Step 6: Testing MCP connection with access token...")
        from mcp_client.client import MCPClient

        sse_endpoint = await get_sse_endpoint(server_url)
        print(f"  - SSE Endpoint: {sse_endpoint}")

        mcp_client = MCPClient(sse_endpoint, token_response['access_token'])
        init_result = await mcp_client.connect()
        print(f"✓ Connected to MCP server!")
        print(f"  - Server Name: {init_result.get('serverInfo', {}).get('name', 'Unknown')}")

        tools = await mcp_client.list_tools()
        print(f"✓ Found {len(tools)} tool(s):")
        for tool in tools:
            print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")

        await mcp_client.disconnect()

        print(f"\n{'='*60}")
        print("✅ OAuth DCR Flow Complete!")
        print(f"{'='*60}\n")

        print("Next steps:")
        print("1. Check greeting_mcp_server/oauth_clients.json for the registered client")
        print("2. In Chrome DevTools Network tab, review all the requests")
        print("3. Verify PKCE code_challenge and code_verifier were used correctly")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await oauth_client.close()


if __name__ == "__main__":
    asyncio.run(test_oauth_flow())
