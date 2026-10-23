# Research Assistant

A platform for looking up and analyzing research papers.

The first feature (KAN-1) is a prototype: enter a research topic and get four significant papers from the last four years, each with a summary and a link to read it.

## How it works

1. The backend computes a window covering the four years before the day of the search.
2. It queries [OpenAlex](https://openalex.org) for articles in that window that have an abstract, most cited first, and keeps the top 25 as candidates.
3. One call to `openai/gpt-oss-120b` via [OpenRouter](https://openrouter.ai) picks the four most significant findings from those candidates and writes a short summary for each.
4. The frontend shows the four papers with title, authors, year, summary, and a "View paper" link (DOI when available).

No database and no caching in this version.

## Project layout

```
backend/    FastAPI service (Python, managed with uv)
frontend/   Next.js app (TypeScript, Tailwind, npm)
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for the backend (Python 3.12 is installed automatically)
- Node.js 20+ and npm for the frontend
- An OpenRouter API key

## Setup

```bash
# Backend
cd backend
cp .env.example .env          # then set OPENROUTER_API_KEY
uv sync

# Frontend
cd ../frontend
npm install
```

Set `OPENROUTER_API_KEY` in `backend/.env`, or export it in your shell. The key is only read by the backend and is never sent to the browser.

## Running

Start the backend and the frontend in two terminals:

```bash
# terminal 1
cd backend
uv run uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm run dev
```

Open http://localhost:3000, enter a topic of at least two characters, and search. A search takes up to a minute because the LLM call runs on every request.

## Tests

```bash
cd backend && uv run pytest
cd frontend && npm test
```

The backend tests use mocked HTTP transports, so they do not need network access or an API key. The frontend tests mock `fetch`.

## API

`GET /api/search?topic=<text>`

```json
{
  "topic": "large language model evaluation",
  "from_date": "2022-10-23",
  "to_date": "2026-10-23",
  "papers": [
    {
      "id": "https://openalex.org/W...",
      "title": "...",
      "authors": ["..."],
      "year": 2025,
      "summary": "...",
      "url": "https://doi.org/..."
    }
  ]
}
```

| Status | Meaning |
| ------ | ------- |
| 200    | Four papers (fewer if the LLM finds fewer usable candidates) |
| 404    | OpenAlex returned no papers with abstracts for the topic and window |
| 422    | Topic missing, shorter than 2 characters, or longer than 200 |
| 502    | OpenAlex or OpenRouter failed, or the LLM reply was unusable after one retry |

`GET /api/health` returns `{"status": "ok"}`.

## Configuration

| Variable | Where | Default | Purpose |
| -------- | ----- | ------- | ------- |
| `OPENROUTER_API_KEY` | backend | (required) | OpenRouter API key |
| `OPENROUTER_MODEL` | backend | `openai/gpt-oss-120b` | Model used for selection and summaries |
| `OPENALEX_MAILTO` | backend | unset | Contact email for the OpenAlex polite pool |
| `FRONTEND_ORIGIN` | backend | `http://localhost:3000` | CORS allowed origin |
| `NEXT_PUBLIC_API_BASE_URL` | frontend | `http://localhost:8000` | Backend address |

## Known limitations

- Each search makes a live OpenAlex call and an LLM call. Nothing is cached, so repeated searches cost more time and API usage.
- "Significance" is the LLM's judgment over the 25 most-cited candidates, so a highly cited paper that is not in that pool cannot appear.
- The LLM reply is parsed as JSON. It is retried once if invalid, then the search returns 502.
