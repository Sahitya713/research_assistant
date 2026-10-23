from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.llm import LLMError, OpenRouterClient
from app.openalex import OpenAlexClient, OpenAlexError
from app.ranking import InvalidSelectionError
from app.schemas import PaperOut, SearchResponse
from app.service import NoPapersFoundError, PaperSearch


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with httpx.AsyncClient(timeout=30.0) as http:
        app.state.http = http
        yield


router = APIRouter()


def create_app() -> FastAPI:
    app = FastAPI(title="Research Assistant API", lifespan=lifespan)
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


def get_paper_search(request: Request, settings: Settings = Depends(get_settings)) -> PaperSearch:
    http: httpx.AsyncClient = request.app.state.http
    openalex = OpenAlexClient(http, mailto=settings.openalex_mailto)
    llm = OpenRouterClient(http, api_key=settings.openrouter_api_key, model=settings.openrouter_model)
    return PaperSearch(openalex, llm)


def get_today() -> date:
    return date.today()


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/search", response_model=SearchResponse)
async def search(
    topic: str = Query(min_length=2, max_length=200),
    search_service: PaperSearch = Depends(get_paper_search),
    today: date = Depends(get_today),
) -> SearchResponse:
    cleaned = topic.strip()
    if len(cleaned) < 2:
        raise HTTPException(status_code=422, detail="Topic must be at least 2 characters")

    try:
        result = await search_service.search(cleaned, today)
    except NoPapersFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OpenAlexError, LLMError, InvalidSelectionError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SearchResponse(
        topic=result.topic,
        from_date=result.from_date,
        to_date=result.to_date,
        papers=[PaperOut(**paper.__dict__) for paper in result.papers],
    )


app = create_app()
