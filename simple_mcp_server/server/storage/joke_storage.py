import json
import threading
from pathlib import Path
from typing import List, Dict
import random


class JokeStorage:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.lock = threading.Lock()
        self._initialize()

    def _initialize(self):
        """Create file with default jokes if it doesn't exist"""
        if not self.file_path.exists():
            default_jokes = [
                {
                    "id": 1,
                    "joke": "Why don't scientists trust atoms? Because they make up everything!",
                    "category": "science"
                },
                {
                    "id": 2,
                    "joke": "Why did the scarecrow win an award? He was outstanding in his field!",
                    "category": "puns"
                },
                {
                    "id": 3,
                    "joke": "What do you call a bear with no teeth? A gummy bear!",
                    "category": "animals"
                },
                {
                    "id": 4,
                    "joke": "Why don't programmers like nature? It has too many bugs!",
                    "category": "programming"
                },
                {
                    "id": 5,
                    "joke": "What's the best thing about Switzerland? I don't know, but the flag is a big plus!",
                    "category": "geography"
                }
            ]
            self._write_jokes(default_jokes)

    def _write_jokes(self, jokes: List[Dict]) -> None:
        """Internal write method (assumes lock is held)"""
        self.file_path.write_text(json.dumps(jokes, indent=2))

    def get_all_jokes(self) -> List[Dict]:
        """Thread-safe read all jokes"""
        with self.lock:
            return json.loads(self.file_path.read_text())

    def get_random_joke(self) -> Dict:
        """Thread-safe get random joke"""
        with self.lock:
            jokes = json.loads(self.file_path.read_text())
            if not jokes:
                return {"error": "No jokes available"}
            return random.choice(jokes)

    def add_joke(self, joke_text: str, category: str = "general") -> Dict:
        """Thread-safe add joke"""
        with self.lock:
            jokes = json.loads(self.file_path.read_text())
            new_id = max([j["id"] for j in jokes], default=0) + 1
            new_joke = {
                "id": new_id,
                "joke": joke_text,
                "category": category
            }
            jokes.append(new_joke)
            self._write_jokes(jokes)
            return new_joke

    def count(self) -> int:
        """Thread-safe count jokes"""
        with self.lock:
            jokes = json.loads(self.file_path.read_text())
            return len(jokes)
