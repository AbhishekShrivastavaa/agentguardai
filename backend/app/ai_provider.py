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
AGENTGUARD_API_KEY = os.getenv("AGENTGUARD_API_KEY")


async def generate_chat_completion(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the configured OpenAI-compatible upstream provider."""
    if not GROQ_API_KEY:
        return {"success": False, "error": "The upstream model provider is not configured."}

    payload: dict[str, Any] = {
        "model": model or GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

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
            return {
                "success": False,
                "error": f"Upstream model provider returned HTTP {response.status_code}.",
            }
        return {"success": True, "data": response.json()}
    except httpx.TimeoutException:
        return {"success": False, "error": "Upstream model provider request timed out."}
    except (httpx.HTTPError, ValueError, TypeError):
        return {"success": False, "error": "Upstream model provider request failed."}


async def generate_ai_response(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    conversation: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Generate a response from Groq using the inspected chat history."""

    result = await generate_chat_completion([
        {"role": "system", "content": system_prompt},
        *(conversation or []),
        {"role": "user", "content": prompt},
    ])
    if not result["success"]:
        return result
    try:
        data = result["data"]
        answer = data["choices"][0]["message"]["content"] or ""
        return {
            "success": True,
            "model": data.get("model", GROQ_MODEL),
            "response": answer,
            "usage": data.get("usage", {}),
        }
    except (KeyError, IndexError, TypeError):
        return {"success": False, "error": "Upstream model provider returned an invalid response."}
