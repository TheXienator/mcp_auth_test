from typing import Dict, List, Any
import re

# I didn't have a claude API key so I had Claude code make a super simple mock claude API that just uses pattern matching to determine which tool to use or just send a message back.
class MockClaude:
    """
    Mocked Claude API that intelligently selects MCP tools based on user intent
    """

    def __init__(self, available_tools: List[Dict]):
        self.available_tools = available_tools
        self.tool_map = {tool["name"]: tool for tool in available_tools}

    def analyze_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Analyze user message and determine which tool to use
        Returns: {
            "tool_name": str,
            "arguments": dict,
            "reasoning": str
        }
        """
        message_lower = user_message.lower()

        # Pattern matching for different intents
        # Order matters! Check more specific patterns first
        patterns = [
            ("save_joke", [
                r'\b(save|add|store|remember)\s+(this\s+)?joke\b',
                r'\bnew\s+joke\b',
            ]),
            ("get_joke", [
                r'\b(tell|give|show)\s+(me\s+)?a\s+joke\b',
                r'\bfunny\b',
                r'\bmake\s+me\s+laugh\b',
                r'\bsomething\s+funny\b',
                r'\bget\s+joke\b',
                r'\bread\s+joke\b',
            ]),
        ]

        # Check patterns for each tool
        for tool_name, tool_patterns in patterns:
            for pattern in tool_patterns:
                if re.search(pattern, message_lower):
                    arguments = self._extract_arguments(tool_name, user_message)
                    reasoning = self._explain_choice(tool_name, pattern, user_message)
                    return {
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "reasoning": reasoning
                    }

        # Default fallback - return message instead of tool call
        return {
            "tool_name": None,
            "arguments": {},
            "reasoning": "No clear intent detected for joke-related operations.",
            "message": "I don't know how to process something that does not ask or save a joke"
        }

    def _extract_arguments(self, tool_name: str, message: str) -> Dict[str, Any]:
        """Extract arguments for the selected tool from the message"""
        if tool_name == "save_joke":
            # Try to extract joke text after keywords
            match = re.search(
                r'(?:save|add|store|remember)\s+(?:this\s+)?(?:joke:\s*)?(.+)',
                message,
                re.IGNORECASE
            )
            if match:
                joke_text = match.group(1).strip()
                # Try to extract category if mentioned
                category_match = re.search(
                    r'category:\s*(\w+)|as\s+(\w+)\s+joke',
                    joke_text,
                    re.IGNORECASE
                )
                category = "general"
                if category_match:
                    category = category_match.group(1) or category_match.group(2)
                    # Remove category from joke text
                    joke_text = re.sub(
                        r'\s*category:\s*\w+|\s+as\s+\w+\s+joke',
                        '',
                        joke_text,
                        flags=re.IGNORECASE
                    ).strip()

                return {"joke": joke_text, "category": category}
            return {"joke": message, "category": "general"}

        elif tool_name == "edit_text":
            # Try to extract new text after keywords
            match = re.search(
                r'(?:edit|update|change|set)\s+(?:the\s+)?text\s+(?:to:\s*)?(.+)',
                message,
                re.IGNORECASE
            )
            if match:
                return {"new_text": match.group(1).strip()}
            return {"new_text": message}

        return {}

    def _explain_choice(self, tool_name: str, pattern: str, message: str) -> str:
        """Generate human-readable reasoning for tool choice"""
        explanations = {
            "get_joke": "User message matches joke request pattern. Detected keywords suggesting they want a joke.",
            "save_joke": "User message matches save joke pattern. They appear to want to store a new joke.",
            "list_text": "User message matches text retrieval pattern. They want to see stored text.",
            "edit_text": "User message matches text editing pattern. They want to update stored text.",
        }
        return explanations.get(tool_name, f"Matched pattern: {pattern}")

    def should_use_tool(self, user_message: str) -> bool:
        """
        Determine if message requires a tool call
        For this demo, we always try to use tools
        """
        return True  # Always attempt tool usage for demo purposes
