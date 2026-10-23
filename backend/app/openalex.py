"""Client for the OpenAlex works API (https://docs.openalex.org)."""

from datetime import date

import httpx

from app.ranking import Candidate, rebuild_abstract

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


class OpenAlexError(RuntimeError):
    """OpenAlex could not be reached or returned an error."""


class OpenAlexClient:
    def __init__(self, http: httpx.AsyncClient, mailto: str | None = None) -> None:
        self._http = http
        self._mailto = mailto

    async def search_works(self, topic: str, start: date, end: date, per_page: int) -> list[Candidate]:
        """Return articles matching `topic` published in [start, end], most cited first."""
        params = {
            "search": topic,
            "filter": (
                f"from_publication_date:{start.isoformat()},"
                f"to_publication_date:{end.isoformat()},"
                "type:article,has_abstract:true"
            ),
            "sort": "cited_by_count:desc",
            "per-page": str(per_page),
        }
        if self._mailto:
            params["mailto"] = self._mailto

        try:
            response = await self._http.get(OPENALEX_WORKS_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenAlexError(f"OpenAlex request failed: {exc}") from exc

        results = response.json().get("results", [])
        return [_to_candidate(work) for work in results]


def _to_candidate(work: dict) -> Candidate:
    doi = work.get("doi")
    landing = (work.get("primary_location") or {}).get("landing_page_url")
    return Candidate(
        id=work["id"],
        title=work.get("display_name") or "Untitled",
        authors=[
            authorship["author"]["display_name"]
            for authorship in work.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ],
        year=work.get("publication_year") or 0,
        publication_date=work.get("publication_date") or "",
        citations=work.get("cited_by_count") or 0,
        abstract=rebuild_abstract(work.get("abstract_inverted_index")),
        url=doi or landing or work["id"],
    )
