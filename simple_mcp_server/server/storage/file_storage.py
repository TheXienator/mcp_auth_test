import threading
from pathlib import Path


class TextStorage:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.lock = threading.Lock()
        self._initialize()

    def _initialize(self):
        """Create file with default content if it doesn't exist"""
        if not self.file_path.exists():
            self.file_path.write_text("Default text content")

    def read(self) -> str:
        """Thread-safe read"""
        with self.lock:
            return self.file_path.read_text()

    def write(self, content: str) -> None:
        """Thread-safe write"""
        with self.lock:
            self.file_path.write_text(content)
