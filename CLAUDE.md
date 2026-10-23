# CLAUDE.md

Project context for Claude Code. Keep this file current when behaviour or decisions change.

## Implemented

Jira KAN-1 (Done): a topic search that returns four significant papers from the last four years, each with a summary and a link.

- **Backend** (`backend/`, FastAPI, uv): `GET /api/search?topic=` and `GET /api/health`.
- **Frontend** (`frontend/`, Next.js 16, App Router, TypeScript, Tailwind, npm): search page, loading and error states, four result cards.
- **Docker**: one image per service and a root `docker-compose.yml`. Frontend host port defaults to 3000 and is set with `FRONTEND_PORT`.
- **Docs**: root `README.md` (setup, API, config), plus short READMEs in `backend/` and `frontend/`.

## Business decisions

- The product is a prototype for looking up recent research on a topic.
- "Recent" means the four years before the day of the search, computed on the server.
- "Significant" means the four most significant findings among the 25 most-cited candidates. Highly cited papers outside that pool cannot appear.
- Papers come from OpenAlex, which is free and needs no key.
- No accounts, no database, no caching. Each search makes a live call.

## Technical decisions

- **Pipeline:** OpenAlex query (article type, has abstract, date window, sorted by citations, 50 fetched, top 25 kept) → one OpenRouter call with model `openai/gpt-oss-120b` that returns JSON with 4 chosen ids and summaries → validation, one retry on invalid JSON, then 502.
- **Backend layout:** `ranking.py` holds pure logic (no I/O). `openalex.py` and `llm.py` are HTTP clients. `service.py` orchestrates one search. `main.py` holds routes and dependency wiring.
- **Errors:** 404 no papers, 422 bad topic (2–200 characters), 502 upstream or LLM failure.
- **Secrets:** `OPENROUTER_API_KEY` is read on the backend only, from the environment or `backend/.env`. It is never sent to the browser or baked into images.
- **Frontend calls the backend directly** at `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`). CORS allows `FRONTEND_ORIGIN`. That value is inlined at build time, so changing it requires a rebuild.
- **Docker:** backend uses `python:3.12-slim` with uv, runs as non-root, and has a health check. Frontend is a multi-stage Node 24 build using Next.js `output: "standalone"`.

## AI call (OpenRouter)

- **Endpoint:** `POST https://openrouter.ai/api/v1/chat/completions` (`backend/app/llm.py`).
- **Model:** `openai/gpt-oss-120b`, set by `OPENROUTER_MODEL`.
- **Parameters:** one user message, `temperature: 0.2`. No `max_tokens` and no `response_format`, so JSON is enforced by the prompt only.
- **Prompt:** built in `ranking.build_selection_prompt`. It contains the topic and up to 25 candidates (id, title, year, citations, abstract). It asks for the 4 most significant papers, each with a 2–3 sentence summary based only on its abstract, as JSON in the shape `{"papers": [{"id", "summary"}]}`.
- **Output handling:** markdown fences are stripped, then the JSON is parsed. Unknown and duplicate ids are dropped. The result is capped at 4. Empty or unusable replies are retried once (`LLM_ATTEMPTS = 2`), then the search returns 502.
- **Usage and cost:** not tracked. The response's `usage` field is not read or logged, so token counts and cost per search are unknown. Each search makes one LLM call on success, or two if the first reply is invalid.
- **Timeout:** the shared `httpx` client uses a 30-second timeout.
- **Testing:** the client and the prompt/parser are covered by pytest with mocked transports. The live model has only been checked manually.

## Commands

```bash
# Backend
cd backend && uv sync && uv run pytest
uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm test && npm run build

# Both
docker compose up -d --build
```

## Testing

- Backend: pytest, with mocked HTTP transports. No network or key needed.
- Frontend: Vitest with Testing Library, `fetch` mocked.

## Known gaps

- Ruff reports three `B008` warnings on FastAPI `Depends(...)` defaults in `backend/app/main.py`. This is the standard FastAPI pattern and is left as-is.
- Each search takes about 20–25 seconds because of the LLM call.
- No code review agents were run on the implementation.
