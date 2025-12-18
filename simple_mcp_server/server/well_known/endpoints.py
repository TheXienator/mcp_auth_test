from fastapi import APIRouter
from config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/.well-known/mcp-resource-metadata.json")
async def protected_resource_metadata():
    """RFC 9728 - Protected Resource Metadata"""
    return {
        "resource": settings.SERVER_URI,
        "authorization_servers": [settings.SERVER_URI]
    }


@router.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata():
    """RFC 8414 - Authorization Server Metadata"""
    return {
        "issuer": settings.SERVER_URI,
        "authorization_endpoint": f"{settings.SERVER_URI}/login",
        "token_endpoint": f"{settings.SERVER_URI}/oauth/token",
        "grant_types_supported": ["client_credentials", "password"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "response_types_supported": ["token"],
        "ui_locales_supported": ["en"],
        # Custom extension to indicate interactive login is available
        "login_url": f"{settings.SERVER_URI}/login"
    }
