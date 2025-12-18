from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)


def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_well_known_endpoints():
    """Test well-known discovery endpoints"""
    # Test resource metadata
    response = client.get("/.well-known/mcp-resource-metadata.json")
    assert response.status_code == 200
    data = response.json()
    assert "authorization_servers" in data
    assert "resource" in data

    # Test authorization server metadata
    response = client.get("/.well-known/oauth-authorization-server")
    assert response.status_code == 200
    data = response.json()
    assert "token_endpoint" in data
    assert "grant_types_supported" in data


def test_oauth_flow():
    """Test full OAuth client credentials flow"""
    # Get token with valid credentials
    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "client_placeholder",
            "client_secret": "placeholder"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    return data["access_token"]


def test_oauth_invalid_credentials():
    """Test OAuth with invalid credentials"""
    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "wrong_client",
            "client_secret": "wrong_secret"
        }
    )
    assert response.status_code == 401


def test_oauth_invalid_grant_type():
    """Test OAuth with invalid grant type"""
    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "client_placeholder",
            "client_secret": "placeholder"
        }
    )
    assert response.status_code == 400


def test_tool_call_without_auth():
    """Test tool call without authentication returns 403"""
    response = client.post(
        "/mcp/v1/tools/call",
        json={"name": "list_text", "arguments": {}}
    )
    assert response.status_code == 403


def test_list_text_tool():
    """Test list_text tool with valid authentication"""
    # Get token
    token = test_oauth_flow()

    # Call list_text
    response = client.post(
        "/mcp/v1/tools/call",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "list_text", "arguments": {}}
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert len(data["content"]) > 0
    assert data["content"][0]["type"] == "text"


def test_edit_text_tool():
    """Test edit_text tool with valid authentication"""
    # Get token
    token = test_oauth_flow()

    # Call edit_text
    new_text = "This is updated test content!"
    response = client.post(
        "/mcp/v1/tools/call",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "edit_text", "arguments": {"new_text": new_text}}
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "successfully" in data["content"][0]["text"].lower()

    # Verify the text was updated
    response = client.post(
        "/mcp/v1/tools/call",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "list_text", "arguments": {}}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"][0]["text"] == new_text


def test_tool_not_found():
    """Test calling a non-existent tool"""
    token = test_oauth_flow()

    response = client.post(
        "/mcp/v1/tools/call",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "nonexistent_tool", "arguments": {}}
    )
    assert response.status_code == 404


def test_list_tools_endpoint():
    """Test listing available tools"""
    token = test_oauth_flow()

    response = client.get(
        "/mcp/v1/tools/list",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert len(data["tools"]) == 2
    tool_names = [tool["name"] for tool in data["tools"]]
    assert "list_text" in tool_names
    assert "edit_text" in tool_names
