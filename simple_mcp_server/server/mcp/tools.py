from server.storage.joke_storage import JokeStorage
from config import get_settings

settings = get_settings()
joke_storage = JokeStorage(settings.JOKE_STORAGE_PATH)


def get_joke_handler() -> str:
    """MCP tool: Get a random joke"""
    joke = joke_storage.get_random_joke()
    if "error" in joke:
        return joke["error"]
    return f"{joke['joke']}\n\nCategory: {joke['category']}"


def save_joke_handler(joke: str, category: str = "general") -> str:
    """MCP tool: Save a new joke"""
    new_joke = joke_storage.add_joke(joke, category)
    total = joke_storage.count()
    return f"Joke saved successfully! (ID: {new_joke['id']})\nTotal jokes: {total}"


# Tool definitions for MCP
TOOLS = {
    "get_joke": {
        "name": "get_joke",
        "description": "Returns a random joke from the collection",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "handler": get_joke_handler
    },
    "save_joke": {
        "name": "save_joke",
        "description": "Saves a new joke to the collection",
        "inputSchema": {
            "type": "object",
            "properties": {
                "joke": {
                    "type": "string",
                    "description": "The joke text to save"
                },
                "category": {
                    "type": "string",
                    "description": "Category of the joke (e.g., 'puns', 'science', 'programming')",
                    "default": "general"
                }
            },
            "required": ["joke"]
        },
        "handler": save_joke_handler
    }
}
