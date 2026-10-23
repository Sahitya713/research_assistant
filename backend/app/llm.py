"""Client for chat completions via OpenRouter (https://openrouter.ai/docs)."""

import httpx

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMError(RuntimeError):
    """OpenRouter could not be reached or returned an unusable response."""


class OpenRouterClient:
    def __init__(self, http: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._http = http
        self._api_key = api_key
        self._model = model

    async def complete(self, prompt: str) -> str:
        """Send a single user prompt and return the assistant's text reply."""
        if not self._api_key:
            raise LLMError("OPENROUTER_API_KEY is not set")

        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            response = await self._http.post(OPENROUTER_CHAT_URL, json=body, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError(f"OpenRouter request failed: {exc}") from exc

        if not content:
            raise LLMError("OpenRouter returned an empty reply")
        return content
