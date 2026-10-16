import os
from typing import Any

import httpx

SEARCH_API_URL = "https://space.ai-builders.com/backend/v1/search/"

WEB_SEARCH_TOOL_DEFINITION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for up-to-date information. "
            "Use when the user asks about recent events, sports results, news, "
            "or anything that may change after your training data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Concise search keywords or question to look up.",
                },
            },
            "required": ["query"],
        },
    },
}


def web_search(query: str, *, max_results: int = 3) -> Any:
    """Call the internal search API and return parsed JSON."""
    api_key = os.getenv("SUPER_MIND_API_KEY")
    if not api_key:
        raise RuntimeError(
            "SUPER_MIND_API_KEY is not set; configure it in the .env file."
        )

    response = httpx.post(
        SEARCH_API_URL,
        json={"keywords": [query], "max_results": max_results},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()
