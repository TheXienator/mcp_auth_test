"""JSON file persistence for server configurations."""

import json
import os
from pathlib import Path
from threading import Lock
from typing import Optional

from .models import RegisteredServer, ServersStorage


class StorageManager:
    """Thread-safe storage manager for server configurations."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize storage manager.

        Args:
            storage_path: Path to JSON storage file.
                         Defaults to ~/.config/mcp_client/servers.json
        """
        if storage_path is None:
            config_dir = Path.home() / ".config" / "mcp_client"
            config_dir.mkdir(parents=True, exist_ok=True)
            storage_path = config_dir / "servers.json"

        self.storage_path = storage_path
        self._lock = Lock()
        self._ensure_file_exists()
        self._set_secure_permissions()

    def _ensure_file_exists(self) -> None:
        """Create storage file if it doesn't exist."""
        if not self.storage_path.exists():
            self._write_storage(ServersStorage())

    def _set_secure_permissions(self) -> None:
        """Set restrictive permissions (0600) on storage file."""
        try:
            os.chmod(self.storage_path, 0o600)
        except Exception:
            pass  # Best effort

    def _read_storage(self) -> ServersStorage:
        """Read storage from JSON file."""
        with self._lock:
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                return ServersStorage(**data)
            except (FileNotFoundError, json.JSONDecodeError):
                return ServersStorage()

    def _write_storage(self, storage: ServersStorage) -> None:
        """Write storage to JSON file."""
        with self._lock:
            with open(self.storage_path, 'w') as f:
                json.dump(storage.model_dump(), f, indent=2, default=str)
            self._set_secure_permissions()

    def load_servers(self) -> list[RegisteredServer]:
        """Load all servers."""
        storage = self._read_storage()
        return storage.servers

    def get_server(self, server_id: str) -> Optional[RegisteredServer]:
        """Get server by ID."""
        storage = self._read_storage()
        return storage.get_server(server_id)

    def save_server(self, server: RegisteredServer) -> None:
        """Save or update a server."""
        storage = self._read_storage()
        storage.add_or_update_server(server)
        self._write_storage(storage)

    def delete_server(self, server_id: str) -> bool:
        """Delete server by ID."""
        storage = self._read_storage()
        if storage.delete_server(server_id):
            self._write_storage(storage)
            return True
        return False


# Global storage instance
_storage: Optional[StorageManager] = None


def get_storage() -> StorageManager:
    """Get global storage instance."""
    global _storage
    if _storage is None:
        _storage = StorageManager()
    return _storage
