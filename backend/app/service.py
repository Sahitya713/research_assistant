"""Orchestrates one search: OpenAlex candidates -> LLM selection and summaries."""

from dataclasses import dataclass
from datetime import date

from app.llm import OpenRouterClient
from app.openalex import OpenAlexClient
from app.ranking import (
    CANDIDATE_POOL_SIZE,
    MAX_PAPERS,
    Candidate,
    InvalidSelectionError,
    build_selection_prompt,
    date_window,
    parse_selection,
    select_candidates,
)

LLM_ATTEMPTS = 2


@dataclass(frozen=True)
class Paper:
    id: str
    title: str
    authors: list[str]
    year: int
    summary: str
    url: str


@dataclass(frozen=True)
class SearchResult:
    topic: str
    from_date: date
    to_date: date
    papers: list[Paper]


class NoPapersFoundError(LookupError):
    """OpenAlex returned no usable papers for the topic and window."""


class PaperSearch:
    def __init__(self, openalex: OpenAlexClient, llm: OpenRouterClient) -> None:
        self._openalex = openalex
        self._llm = llm

    async def search(self, topic: str, today: date) -> SearchResult:
        start, end = date_window(today)
        works = await self._openalex.search_works(topic, start, end, per_page=CANDIDATE_POOL_SIZE * 2)
        pool = select_candidates(works)
        if not pool:
            raise NoPapersFoundError(f"No papers found for {topic!r} between {start} and {end}")

        selections = await self._select_with_retry(topic, pool)
        by_id = {candidate.id: candidate for candidate in pool}
        papers = [_to_paper(by_id[s.id], s.summary) for s in selections]
        return SearchResult(topic=topic, from_date=start, to_date=end, papers=papers)

    async def _select_with_retry(self, topic: str, pool: list[Candidate]):
        prompt = build_selection_prompt(topic, pool, MAX_PAPERS)
        valid_ids = {candidate.id for candidate in pool}
        last_error: InvalidSelectionError | None = None
        for _ in range(LLM_ATTEMPTS):
            reply = await self._llm.complete(prompt)
            try:
                return parse_selection(reply, valid_ids, MAX_PAPERS)
            except InvalidSelectionError as exc:
                last_error = exc
        raise last_error  # type: ignore[misc]


def _to_paper(candidate: Candidate, summary: str) -> Paper:
    return Paper(
        id=candidate.id,
        title=candidate.title,
        authors=candidate.authors,
        year=candidate.year,
        summary=summary,
        url=candidate.url,
    )
