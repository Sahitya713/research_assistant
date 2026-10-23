import json
from datetime import date

import httpx
import pytest

from app.llm import LLMError, OpenRouterClient
from app.openalex import OpenAlexClient, OpenAlexError


def openalex_work(**overrides) -> dict:
    work = {
        "id": "https://openalex.org/W1",
        "display_name": "Attention Is All You Need Again",
        "publication_year": 2025,
        "publication_date": "2025-03-01",
        "cited_by_count": 42,
        "doi": "https://doi.org/10.1/abc",
        "primary_location": {"landing_page_url": "https://example.org/paper"},
        "authorships": [
            {"author": {"display_name": "Ada Lovelace"}},
            {"author": {"display_name": "Alan Turing"}},
        ],
        "abstract_inverted_index": {"We": [0], "study": [1], "transformers": [2]},
    }
    work.update(overrides)
    return work


async def test_openalex_sends_window_topic_and_sort_then_normalizes_results():
    captured: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = request.url
        return httpx.Response(200, json={"results": [openalex_work()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenAlexClient(http, mailto="me@example.com")
        works = await client.search_works("transformers", date(2022, 1, 1), date(2026, 1, 1), per_page=50)

    params = captured["url"].params
    assert params["search"] == "transformers"
    assert params["sort"] == "cited_by_count:desc"
    assert params["per-page"] == "50"
    assert params["mailto"] == "me@example.com"
    assert "from_publication_date:2022-01-01" in params["filter"]
    assert "to_publication_date:2026-01-01" in params["filter"]
    assert "has_abstract:true" in params["filter"]

    [work] = works
    assert work.title == "Attention Is All You Need Again"
    assert work.authors == ["Ada Lovelace", "Alan Turing"]
    assert work.year == 2025
    assert work.citations == 42
    assert work.abstract == "We study transformers"
    assert work.url == "https://doi.org/10.1/abc"


async def test_openalex_falls_back_to_landing_page_then_openalex_id():
    works_payload = {
        "results": [
            openalex_work(doi=None),
            openalex_work(id="https://openalex.org/W2", doi=None, primary_location=None),
        ]
    }
    handler = lambda request: httpx.Response(200, json=works_payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        works = await OpenAlexClient(http).search_works("x", date(2022, 1, 1), date(2026, 1, 1), 10)

    assert works[0].url == "https://example.org/paper"
    assert works[1].url == "https://openalex.org/W2"


async def test_openalex_wraps_http_errors():
    handler = lambda request: httpx.Response(500)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(OpenAlexError):
            await OpenAlexClient(http).search_works("x", date(2022, 1, 1), date(2026, 1, 1), 10)


async def test_openrouter_posts_model_prompt_and_returns_content():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenRouterClient(http, api_key="sk-test", model="openai/gpt-oss-120b")
        reply = await client.complete("prompt text")

    assert reply == "hello"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"]["model"] == "openai/gpt-oss-120b"
    assert captured["body"]["messages"] == [{"role": "user", "content": "prompt text"}]


async def test_openrouter_requires_api_key():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as http:
        with pytest.raises(LLMError, match="OPENROUTER_API_KEY"):
            await OpenRouterClient(http, api_key="", model="m").complete("x")


async def test_openrouter_wraps_malformed_responses():
    handler = lambda request: httpx.Response(200, json={"choices": []})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(LLMError):
            await OpenRouterClient(http, api_key="k", model="m").complete("x")
