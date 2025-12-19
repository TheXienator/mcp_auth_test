#!/usr/bin/env python3
"""Main entry point for Dynamic MCP Client web interface."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=3000,
        reload=True
    )
