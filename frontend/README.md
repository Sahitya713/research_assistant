# Research Assistant frontend

Next.js (App Router, TypeScript, Tailwind) UI for the research assistant. Enter a topic and it shows four significant papers from the last four years, each with a summary and a link.

The UI calls the FastAPI backend in `../backend`, so start that first. See the [root README](../README.md) for the full setup.

## Commands

```bash
npm install
npm run dev        # http://localhost:3000
npm test           # Vitest + Testing Library
npm run lint
npm run build
```

## Configuration

`NEXT_PUBLIC_API_BASE_URL` sets the backend address. It defaults to `http://localhost:8000`. See `.env.example`.

## Layout

- `app/page.tsx`: the search page (client component, holds the request state).
- `components/`: `SearchForm` and `PaperCard`.
- `lib/api.ts`: typed client for `GET /api/search`.
- `__tests__/`: unit tests for the API client, components, and page.
