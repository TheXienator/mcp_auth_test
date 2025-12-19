"""Dynamic Client Registration (RFC 7591) endpoint."""

import secrets
import uuid
from fastapi import APIRouter, HTTPException, status
from oauth.storage import get_storage
from oauth.schemas.dcr import (
    ClientRegistrationRequest,
    ClientRegistrationResponse,
    ClientRegistrationError
)

router = APIRouter()

# Configuration
BASE_URL = "http://localhost:8000"


@router.post("/register", response_model=ClientRegistrationResponse)
async def register_client(request: ClientRegistrationRequest):
    """RFC 7591 Dynamic Client Registration endpoint.

    Allows clients to register themselves dynamically without manual configuration.

    Args:
        request: Client registration request

    Returns:
        ClientRegistrationResponse with client_id and client_secret

    Raises:
        HTTPException: If registration fails
    """
    # Generate unique client ID
    client_id = str(uuid.uuid4())

    # Generate secure client secret (32 bytes = 256 bits)
    client_secret = secrets.token_urlsafe(32)

    # Generate registration access token
    registration_access_token = secrets.token_urlsafe(32)

    # Default redirect URIs if not provided
    redirect_uris = request.redirect_uris or []

    # Default grant types
    grant_types = request.grant_types or ["client_credentials"]

    # Get storage
    storage = get_storage()

    # Create client
    try:
        client = storage.create_client(
            client_id=client_id,
            client_secret=client_secret,
            client_name=request.client_name,
            redirect_uris=redirect_uris,
            grant_types=grant_types,
            registration_access_token=registration_access_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ClientRegistrationError(
                error="server_error",
                error_description=f"Failed to create client: {str(e)}"
            ).model_dump()
        )

    # Return registration response
    return ClientRegistrationResponse(
        client_id=client.client_id,
        client_secret=client.client_secret,
        client_name=client.client_name,
        redirect_uris=client.redirect_uris,
        grant_types=client.grant_types,
        token_endpoint_auth_method=request.token_endpoint_auth_method or "client_secret_post",
        registration_access_token=registration_access_token,
        registration_client_uri=f"{BASE_URL}/register/{client_id}"
    )


@router.get("/register/{client_id}")
async def get_client_configuration(client_id: str):
    """Get client configuration.

    This endpoint would typically require the registration_access_token
    for authentication. For simplicity, we'll allow unauthenticated access
    in this implementation.

    Args:
        client_id: Client identifier

    Returns:
        Client configuration

    Raises:
        HTTPException: If client not found
    """
    storage = get_storage()
    client = storage.get_client(client_id)

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ClientRegistrationError(
                error="invalid_client_id",
                error_description=f"Client '{client_id}' not found"
            ).model_dump()
        )

    return {
        "client_id": client.client_id,
        "client_name": client.client_name,
        "redirect_uris": client.redirect_uris,
        "grant_types": client.grant_types,
        "registration_client_uri": f"{BASE_URL}/register/{client_id}"
    }
