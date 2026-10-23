"""Pure functions for the search pipeline: date windows, candidate selection,
abstract reconstruction, prompt building, and parsing the LLM's selection.

Nothing in this module performs I/O, so it is easy to unit test.
"""

import json
import re
from dataclasses import dataclass
from datetime import date

MAX_PAPERS = 4
CANDIDATE_POOL_SIZE = 25
WINDOW_YEARS = 4


@dataclass(frozen=True)
class Candidate:
    id: str
    title: str
    authors: list[str]
    year: int
    publication_date: str
    citations: int
    abstract: str
    url: str


def date_window(today: date, years: int = WINDOW_YEARS) -> tuple[date, date]:
    """Return (start, end) covering the `years` years before `today`.

    Feb 29 maps to Feb 28 when the start year is not a leap year.
    """
    try:
        start = today.replace(year=today.year - years)
    except ValueError:
        start = today.replace(year=today.year - years, day=28)
    return start, today


def rebuild_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """OpenAlex stores abstracts as {word: [positions]}. Rebuild the plain text."""
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for word, indexes in inverted_index.items():
        for index in indexes:
            positions[index] = word
    return " ".join(positions[i] for i in sorted(positions))


def select_candidates(candidates: list[Candidate], pool_size: int = CANDIDATE_POOL_SIZE) -> list[Candidate]:
    """Keep candidates with an abstract, ordered by citations, capped at `pool_size`."""
    with_abstract = [c for c in candidates if c.abstract]
    ranked = sorted(with_abstract, key=lambda c: c.citations, reverse=True)
    return ranked[:pool_size]


def build_selection_prompt(topic: str, candidates: list[Candidate], max_papers: int = MAX_PAPERS) -> str:
    lines = [
        f"Research topic: {topic}",
        "",
        f"Below are {len(candidates)} recent research papers on this topic.",
        f"Choose the {max_papers} papers whose findings are most significant for the topic.",
        "For each chosen paper, write a 2-3 sentence summary of its key findings, based only on its abstract.",
        "",
        "Respond with JSON only, in this exact shape:",
        '{"papers": [{"id": "<paper id>", "summary": "<summary>"}]}',
        "",
        "Papers:",
    ]
    for candidate in candidates:
        lines.append("")
        lines.append(f"id: {candidate.id}")
        lines.append(f"title: {candidate.title}")
        lines.append(f"year: {candidate.year}, citations: {candidate.citations}")
        lines.append(f"abstract: {candidate.abstract}")
    return "\n".join(lines)


@dataclass(frozen=True)
class Selection:
    id: str
    summary: str


class InvalidSelectionError(ValueError):
    """The LLM response did not contain a usable selection."""


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_selection(text: str, valid_ids: set[str], max_papers: int = MAX_PAPERS) -> list[Selection]:
    """Parse the LLM's JSON reply into selections that reference known candidate ids.

    Tolerates markdown code fences. Drops unknown and duplicate ids. Raises
    InvalidSelectionError when nothing usable remains.
    """
    cleaned = _FENCE.sub("", text).strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise InvalidSelectionError("LLM response was not valid JSON") from exc

    items = payload.get("papers") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise InvalidSelectionError("LLM response is missing a 'papers' list")

    selections: list[Selection] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = item.get("id")
        summary = item.get("summary")
        if paper_id not in valid_ids or paper_id in seen or not isinstance(summary, str):
            continue
        seen.add(paper_id)
        selections.append(Selection(id=paper_id, summary=summary.strip()))
        if len(selections) == max_papers:
            break

    if not selections:
        raise InvalidSelectionError("LLM selected no valid papers")
    return selections
