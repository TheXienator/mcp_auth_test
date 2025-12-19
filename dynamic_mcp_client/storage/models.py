"""Pydantic models for persistent storage."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class RegisteredServer(BaseModel):
    """Registered MCP server configuration."""

    # Basic info
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    server_url: str
    transport_type: str = "sse"

    # DCR data (from /register response)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    registration_access_token: Optional[str] = None
    registration_client_uri: Optional[str] = None

    # OAuth tokens
    access_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    token_expires_at: Optional[datetime] = None
    refresh_token: Optional[str] = None

    # Cached OAuth metadata
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    sse_endpoint: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_connected: Optional[datetime] = None

    @property
    def is_registered(self) -> bool:
        """Check if DCR registration is complete."""
        return self.client_id is not None and self.client_secret is not None

    @property
    def is_authorized(self) -> bool:
        """Check if OAuth authorization is complete."""
        return self.access_token is not None

    @property
    def is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.token_expires_at:
            return True
        return datetime.utcnow() >= self.token_expires_at


class ServersStorage(BaseModel):
    """Root storage model."""

    servers: list[RegisteredServer] = Field(default_factory=list)

    def get_server(self, server_id: str) -> Optional[RegisteredServer]:
        """Get server by ID."""
        for server in self.servers:
            if server.id == server_id:
                return server
        return None

    def add_or_update_server(self, server: RegisteredServer) -> None:
        """Add new server or update existing one."""
        existing = self.get_server(server.id)
        if existing:
            # Update existing
            self.servers.remove(existing)
        self.servers.append(server)

    def delete_server(self, server_id: str) -> bool:
        """Delete server by ID."""
        server = self.get_server(server_id)
        if server:
            self.servers.remove(server)
            return True
        return False
