# Research Assistant backend

FastAPI service that finds recent, significant papers for a topic. It uses OpenAlex for paper data and OpenRouter (`openai/gpt-oss-120b`) for selection and summaries. Managed with [uv](https://docs.astral.sh/uv/).

See the [root README](../README.md) for the full pipeline, API contract, and configuration.

## Commands

```bash
uv sync                                        # install dependencies
uv run uvicorn app.main:app --reload --port 8000
uv run pytest                                  # tests, no network needed
```

## Layout

- `app/main.py`: FastAPI app, CORS, routes, and dependency wiring.
- `app/service.py`: orchestrates one search (OpenAlex, then LLM, with one retry).
- `app/ranking.py`: pure functions for the date window, candidate selection, prompt building, and parsing the LLM's JSON. No I/O.
- `app/openalex.py`, `app/llm.py`: HTTP clients for OpenAlex and OpenRouter.
- `app/config.py`: settings read from the environment or `.env`.
- `tests/`: unit tests for ranking and clients (mocked transports), service tests, and API tests.
