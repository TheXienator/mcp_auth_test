"""Client storage for OAuth clients."""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List
import threading


@dataclass
class OAuthClient:
    """OAuth client model."""
    client_id: str
    client_secret: str
    client_name: str
    redirect_uris: List[str]
    grant_types: List[str]
    registration_access_token: str
    created_at: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OAuthClient":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AuthorizationCode:
    """Authorization code model."""
    code: str
    client_id: str
    redirect_uri: str
    code_challenge: Optional[str]
    code_challenge_method: str
    scope: str
    created_at: str
    used: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AuthorizationCode":
        """Create from dictionary."""
        return cls(**data)


class ClientStorage:
    """Thread-safe client storage.

    Supports both in-memory and file-based persistence.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize storage.

        Args:
            storage_path: Optional path to JSON file for persistence
        """
        self.storage_path = storage_path
        self._clients: Dict[str, OAuthClient] = {}
        self._auth_codes: Dict[str, AuthorizationCode] = {}
        self._lock = threading.Lock()

        # Load from file if path provided and file exists
        if storage_path and storage_path.exists():
            self._load_from_file()

    def _load_from_file(self) -> None:
        """Load clients from JSON file."""
        if not self.storage_path:
            return

        try:
            with self._lock:
                data = json.loads(self.storage_path.read_text())
                self._clients = {
                    client_id: OAuthClient.from_dict(client_data)
                    for client_id, client_data in data.items()
                }
                print(f"Loaded {len(self._clients)} clients from {self.storage_path}")
        except Exception as e:
            print(f"Error loading clients from file: {e}")

    def _save_to_file(self) -> None:
        """Save clients to JSON file."""
        if not self.storage_path:
            return

        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to file
            data = {
                client_id: client.to_dict()
                for client_id, client in self._clients.items()
            }
            self.storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error saving clients to file: {e}")

    def create_client(
        self,
        client_id: str,
        client_secret: str,
        client_name: str,
        redirect_uris: List[str],
        grant_types: List[str],
        registration_access_token: str
    ) -> OAuthClient:
        """Create and store a new client.

        Args:
            client_id: Unique client identifier
            client_secret: Client secret
            client_name: Human-readable client name
            redirect_uris: List of allowed redirect URIs
            grant_types: List of allowed grant types
            registration_access_token: Token for client management

        Returns:
            Created OAuthClient
        """
        client = OAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            client_name=client_name,
            redirect_uris=redirect_uris,
            grant_types=grant_types,
            registration_access_token=registration_access_token,
            created_at=datetime.now(timezone.utc).isoformat()
        )

        with self._lock:
            self._clients[client_id] = client
            self._save_to_file()

        return client

    def get_client(self, client_id: str) -> Optional[OAuthClient]:
        """Get client by ID.

        Args:
            client_id: Client identifier

        Returns:
            OAuthClient if found, None otherwise
        """
        with self._lock:
            return self._clients.get(client_id)

    def validate_credentials(self, client_id: str, client_secret: str) -> bool:
        """Validate client credentials.

        Args:
            client_id: Client identifier
            client_secret: Client secret

        Returns:
            True if credentials are valid, False otherwise
        """
        client = self.get_client(client_id)
        if not client:
            return False

        return client.client_secret == client_secret

    def delete_client(self, client_id: str) -> bool:
        """Delete client.

        Args:
            client_id: Client identifier

        Returns:
            True if client was deleted, False if not found
        """
        with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                self._save_to_file()
                return True
            return False

    def list_clients(self) -> List[OAuthClient]:
        """List all clients.

        Returns:
            List of all OAuthClients
        """
        with self._lock:
            return list(self._clients.values())

    def store_authorization_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: Optional[str],
        code_challenge_method: str,
        scope: str
    ) -> AuthorizationCode:
        """Store an authorization code.

        Args:
            code: The authorization code
            client_id: Client identifier
            redirect_uri: Redirect URI used in authorization request
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method
            scope: Requested scope

        Returns:
            Created AuthorizationCode
        """
        auth_code_obj = AuthorizationCode(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            scope=scope,
            created_at=datetime.now(timezone.utc).isoformat(),
            used=False
        )

        with self._lock:
            self._auth_codes[code] = auth_code_obj

        return auth_code_obj

    def get_authorization_code(self, code: str) -> Optional[AuthorizationCode]:
        """Get authorization code.

        Args:
            code: The authorization code

        Returns:
            AuthorizationCode if found and not used, None otherwise
        """
        with self._lock:
            auth_code = self._auth_codes.get(code)
            if auth_code and not auth_code.used:
                return auth_code
            return None

    def mark_code_as_used(self, code: str) -> bool:
        """Mark authorization code as used.

        Args:
            code: The authorization code

        Returns:
            True if code was marked as used, False if not found
        """
        with self._lock:
            auth_code = self._auth_codes.get(code)
            if auth_code:
                auth_code.used = True
                return True
            return False


# Global storage instance
_storage: Optional[ClientStorage] = None
_storage_lock = threading.Lock()


def get_storage(storage_path: Optional[Path] = None) -> ClientStorage:
    """Get global storage instance.

    Args:
        storage_path: Optional path to JSON file for persistence

    Returns:
        ClientStorage instance
    """
    global _storage

    with _storage_lock:
        if _storage is None:
            _storage = ClientStorage(storage_path)
        return _storage
