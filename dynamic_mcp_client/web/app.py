"""FastAPI web application for Dynamic MCP Client."""

import secrets
import json
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import webbrowser

from oauth.client import OAuthClient
from oauth.pkce import generate_pkce_pair
from oauth.browser import open_browser_and_get_code
from mcp_client.discovery import get_sse_endpoint
from mcp_client.client import MCPClient
from storage.models import RegisteredServer
from storage.persistence import get_storage


app = FastAPI(title="Dynamic MCP Client")

# Setup templates and static files
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Server list page."""
    servers = get_storage().load_servers()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "servers": servers}
    )


@app.get("/add", response_class=HTMLResponse)
async def add_server_form(request: Request):
    """Add server form page."""
    return templates.TemplateResponse(
        "add_server.html",
        {"request": request}
    )


@app.post("/add/check")
async def check_server(name: str = Form(...), url: str = Form(...)):
    """
    Check server and perform DCR registration.

    Returns JSON with server details or error.
    """
    try:
        # Create OAuth client
        oauth_client = OAuthClient(url)

        # Discover OAuth metadata
        metadata = await oauth_client.discover_oauth_metadata()

        # Perform DCR
        redirect_uri = "http://localhost:8080/callback"
        dcr_response = await oauth_client.register_client(
            client_name=f"Dynamic MCP Client - {name}",
            redirect_uri=redirect_uri
        )

        # Get SSE endpoint
        sse_endpoint = await get_sse_endpoint(url)

        # Create server record (without tokens yet)
        server = RegisteredServer(
            name=name,
            server_url=url,
            transport_type="sse",
            client_id=dcr_response["client_id"],
            client_secret=dcr_response["client_secret"],
            registration_access_token=dcr_response.get("registration_access_token"),
            registration_client_uri=dcr_response.get("registration_client_uri"),
            authorization_endpoint=metadata["authorization_endpoint"],
            token_endpoint=metadata["token_endpoint"],
            sse_endpoint=sse_endpoint
        )

        # Save to storage
        get_storage().save_server(server)

        await oauth_client.close()

        return JSONResponse({
            "success": True,
            "server_id": server.id,
            "client_id": server.client_id,
            "message": "Server registered successfully!"
        })

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=400
        )


@app.post("/add/connect/{server_id}")
async def connect_server(server_id: str):
    """
    Perform OAuth authorization and token exchange.

    Opens browser for user authorization.
    """
    try:
        server = get_storage().get_server(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        # Create OAuth client
        oauth_client = OAuthClient(server.server_url)

        # Generate PKCE
        code_verifier, code_challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(16)

        # Build authorization URL
        redirect_uri = "http://localhost:8080/callback"
        auth_url = oauth_client.build_authorization_url(
            authorization_endpoint=server.authorization_endpoint,
            client_id=server.client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge
        )

        # Open browser and wait for callback
        code = await open_browser_and_get_code(auth_url, redirect_uri, state)

        # Exchange code for token
        token_response = await oauth_client.exchange_code_for_token(
            token_endpoint=server.token_endpoint,
            code=code,
            client_id=server.client_id,
            client_secret=server.client_secret,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )

        # Update server with tokens
        server.access_token = token_response["access_token"]
        server.token_type = token_response.get("token_type", "Bearer")
        server.expires_in = token_response.get("expires_in")
        if server.expires_in:
            server.token_expires_at = datetime.utcnow() + timedelta(
                seconds=server.expires_in
            )
        server.refresh_token = token_response.get("refresh_token")
        server.last_connected = datetime.utcnow()

        # Save updated server
        get_storage().save_server(server)

        await oauth_client.close()

        return JSONResponse({
            "success": True,
            "message": "Connected successfully!"
        })

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=400
        )


@app.get("/servers/{server_id}/tools")
async def get_tools(server_id: str):
    """
    Get tools for a server using MCP protocol.
    
    This endpoint uses the MCP client which internally sends a JSON-RPC
    'tools/list' request to the MCP server over SSE transport.
    """
    try:
        server = get_storage().get_server(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        if not server.is_authorized:
            return JSONResponse(
                {"success": False, "error": "Server not authorized"},
                status_code=400
            )

        if server.is_token_expired:
            return JSONResponse(
                {"success": False, "error": "Token expired. Please re-authorize."},
                status_code=400
            )

        # Validate required fields
        if not server.sse_endpoint:
            return JSONResponse(
                {"success": False, "error": "SSE endpoint not configured"},
                status_code=400
            )
        
        if not server.access_token:
            return JSONResponse(
                {"success": False, "error": "Access token not available"},
                status_code=400
            )

        # Create MCP client (uses SSE transport with OAuth Bearer token)
        mcp_client = MCPClient(server.sse_endpoint, server.access_token)

        try:
            # Connect to MCP server (sends initialize request via JSON-RPC)
            init_result = await mcp_client.connect()
            server_name = init_result.serverInfo.name if hasattr(init_result, 'serverInfo') and hasattr(init_result.serverInfo, 'name') else 'Unknown'

            # List tools using MCP protocol (sends 'tools/list' JSON-RPC request)
            tools = await mcp_client.list_tools()
            tool_list = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                }
                for tool in tools
            ]

            return JSONResponse({
                "success": True,
                "server_name": server_name,
                "tools": tool_list
            })
        except Exception as connect_error:
            # Log the full error for debugging
            error_trace = traceback.format_exc()
            logging.error(f"MCP connection error for server {server_id}: {error_trace}")
            
            # Return more detailed error
            error_msg = str(connect_error)
            if "TaskGroup" in error_msg:
                error_msg = f"Connection error: Failed to establish connection to MCP server at {server.sse_endpoint}. Check if the server is running and the access token is valid."
            raise  # Re-raise to be caught by outer except
        finally:
            # Always cleanup, even if there's an error
            try:
                await mcp_client.disconnect()
            except Exception as cleanup_error:
                # Log but don't fail on cleanup errors
                logging.warning(f"Error during MCP client cleanup: {cleanup_error}")

    except Exception as e:
        # Extract more detailed error information
        error_trace = traceback.format_exc()
        logging.error(f"Error in get_tools endpoint: {error_trace}")
        
        error_msg = str(e)
        if "TaskGroup" in error_msg:
            error_msg = f"Connection error: Failed to establish connection to MCP server. Full error: {error_msg}"
        return JSONResponse(
            {"success": False, "error": error_msg},
            status_code=400
        )


@app.post("/servers/{server_id}/test")
async def test_connection(server_id: str):
    """Test MCP connection to a server."""
    try:
        server = get_storage().get_server(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        if not server.is_authorized:
            return JSONResponse(
                {"success": False, "error": "Server not authorized"},
                status_code=400
            )

        if server.is_token_expired:
            return JSONResponse(
                {"success": False, "error": "Token expired. Please re-authorize."},
                status_code=400
            )

        # Validate required fields
        if not server.sse_endpoint:
            return JSONResponse(
                {"success": False, "error": "SSE endpoint not configured"},
                status_code=400
            )
        
        if not server.access_token:
            return JSONResponse(
                {"success": False, "error": "Access token not available"},
                status_code=400
            )

        # Create MCP client
        mcp_client = MCPClient(server.sse_endpoint, server.access_token)

        try:
            # Connect
            init_result = await mcp_client.connect()
            server_name = init_result.serverInfo.name if hasattr(init_result, 'serverInfo') and hasattr(init_result.serverInfo, 'name') else 'Unknown'

            # List tools
            tools = await mcp_client.list_tools()
            tool_list = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                }
                for tool in tools
            ]

            # Update last connected time
            server.last_connected = datetime.utcnow()
            get_storage().save_server(server)

            return JSONResponse({
                "success": True,
                "server_name": server_name,
                "tools": tool_list,
                "message": f"Connected to {server_name}! Found {len(tools)} tool(s)."
            })
        except Exception as connect_error:
            # Log the full error for debugging
            error_trace = traceback.format_exc()
            logging.error(f"MCP connection error for server {server_id}: {error_trace}")
            
            # Return more detailed error
            error_msg = str(connect_error)
            if "TaskGroup" in error_msg:
                error_msg = f"Connection error: Failed to establish connection to MCP server at {server.sse_endpoint}. Check if the server is running and the access token is valid."
            raise  # Re-raise to be caught by outer except
        finally:
            # Always cleanup, even if there's an error
            try:
                await mcp_client.disconnect()
            except Exception as cleanup_error:
                # Log but don't fail on cleanup errors
                logging.warning(f"Error during MCP client cleanup: {cleanup_error}")

    except Exception as e:
        # Extract more detailed error information
        error_trace = traceback.format_exc()
        logging.error(f"Error in test_connection endpoint: {error_trace}")
        
        error_msg = str(e)
        if "TaskGroup" in error_msg:
            error_msg = f"Connection error: Failed to establish connection to MCP server. Full error: {error_msg}"
        return JSONResponse(
            {"success": False, "error": error_msg},
            status_code=400
        )


@app.post("/servers/{server_id}/call-tool")
async def call_tool_endpoint(server_id: str, tool_name: str = Form(...), arguments: str = Form(...)):
    """Execute a tool with provided arguments."""
    try:
        server = get_storage().get_server(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        if not server.is_authorized:
            return JSONResponse(
                {"success": False, "error": "Server not authorized"},
                status_code=400
            )

        if server.is_token_expired:
            return JSONResponse(
                {"success": False, "error": "Token expired. Please re-authorize."},
                status_code=400
            )

        # Parse arguments JSON string
        try:
            arguments_dict = json.loads(arguments)
        except json.JSONDecodeError as e:
            return JSONResponse(
                {"success": False, "error": f"Invalid JSON in arguments: {str(e)}"},
                status_code=400
            )

        # Create MCP client and connect
        mcp_client = MCPClient(server.sse_endpoint, server.access_token)
        
        try:
            await mcp_client.connect()
            
            # Call tool
            result = await mcp_client.call_tool(tool_name, arguments_dict)

            # Extract result content - handle TextContent and other MCP result types
            result_content = None
            
            if hasattr(result, 'content'):
                content = result.content
                # Handle TextContent objects - extract the text property
                if hasattr(content, 'text'):
                    result_content = content.text
                elif hasattr(content, '__iter__') and not isinstance(content, (str, bytes)):
                    # Handle list of content items
                    content_list = []
                    for item in content:
                        if hasattr(item, 'text'):
                            content_list.append(item.text)
                        else:
                            content_list.append(str(item))
                    result_content = '\n'.join(content_list) if content_list else ''
                else:
                    result_content = str(content) if content is not None else ''
            elif hasattr(result, 'text'):
                result_content = result.text
            else:
                # Try to convert to string or JSON
                try:
                    # Check if it's a Pydantic model or similar
                    if hasattr(result, 'model_dump'):
                        result_dict = result.model_dump()
                        result_content = json.dumps(result_dict, default=str, indent=2)
                    elif isinstance(result, (dict, list)):
                        result_content = json.dumps(result, default=str, indent=2)
                    else:
                        result_content = str(result)
                except Exception as e:
                    logging.warning(f"Error serializing result: {e}")
                    result_content = str(result)
            
            # Ensure result_content is a string
            if result_content is None:
                result_content = ''
            elif not isinstance(result_content, str):
                result_content = str(result_content)

            return JSONResponse({
                "success": True,
                "result": result_content,
                "tool_name": tool_name
            })
        finally:
            # Always disconnect, even if there's an error
            try:
                await mcp_client.disconnect()
            except Exception as cleanup_error:
                # Log but don't fail on cleanup errors
                logging.warning(f"Error during MCP client cleanup: {cleanup_error}")

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=400
        )


@app.post("/servers/{server_id}/delete")
async def delete_server(server_id: str):
    """Delete a server."""
    try:
        server = get_storage().get_server(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        server_name = server.name
        get_storage().delete_server(server_id)

        return JSONResponse({
            "success": True,
            "message": f"Deleted server: {server_name}"
        })

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=400
        )
