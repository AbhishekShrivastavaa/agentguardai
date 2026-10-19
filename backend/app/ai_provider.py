import os
from typing import Any

import httpx
from dotenv import load_dotenv

# Load backend/.env
ENV_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".env")
)
load_dotenv(ENV_PATH)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)
GROQ_BASE_URL = os.getenv(
    "GROQ_BASE_URL",
    "https://api.groq.com/openai/v1",
).rstrip("/")


async def generate_ai_response(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    conversation: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Generate a response from Groq using the inspected chat history."""

    if not GROQ_API_KEY:
        return {
            "success": False,
            "error": "GROQ_API_KEY is missing from backend/.env",
        }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            *(conversation or []),
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{GROQ_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.is_error:
            # Don't expose API keys or raw provider responses.
            return {
                "success": False,
                "error": f"Groq API returned HTTP {response.status_code}. "
                + ("Check the configured model ID and model access." if response.status_code == 404 else "Check provider credentials and account limits."),
            }

        data = response.json()
        answer = data["choices"][0]["message"]["content"]

        return {
            "success": True,
            "model": data.get("model", GROQ_MODEL),
            "response": answer,
            "usage": data.get("usage", {}),
        }

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Groq API request timed out.",
        }
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        return {
            "success": False,
            "error": "Groq API request failed or returned an invalid response.",
        }
