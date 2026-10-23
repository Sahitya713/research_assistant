from datetime import date

import pytest

from app.ranking import Candidate, InvalidSelectionError
from app.service import NoPapersFoundError, PaperSearch


def candidate(paper_id: str, citations: int, abstract: str = "Abstract text.") -> Candidate:
    return Candidate(
        id=paper_id,
        title=f"Title {paper_id}",
        authors=["Ada Lovelace"],
        year=2025,
        publication_date="2025-01-01",
        citations=citations,
        abstract=abstract,
        url=f"https://doi.org/{paper_id}",
    )


class FakeOpenAlex:
    def __init__(self, works: list[Candidate]) -> None:
        self.works = works
        self.calls: list[tuple[str, date, date, int]] = []

    async def search_works(self, topic, start, end, per_page):
        self.calls.append((topic, start, end, per_page))
        return self.works


class ScriptedLLM:
    """Returns the scripted replies in order, one per call."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.replies.pop(0)


async def test_search_selects_papers_and_reports_window():
    works = [candidate("W1", 90), candidate("W2", 40), candidate("W3", 5)]
    openalex = FakeOpenAlex(works)
    llm = ScriptedLLM(['{"papers": [{"id": "W2", "summary": "Found X."}, {"id": "W1", "summary": "Found Y."}]}'])

    result = await PaperSearch(openalex, llm).search("graphs", today=date(2026, 10, 23))

    assert result.from_date == date(2022, 10, 23)
    assert result.to_date == date(2026, 10, 23)
    assert openalex.calls[0][:3] == ("graphs", date(2022, 10, 23), date(2026, 10, 23))
    assert [p.id for p in result.papers] == ["W2", "W1"]
    assert result.papers[0].summary == "Found X."
    assert result.papers[0].title == "Title W2"
    assert result.papers[0].url == "https://doi.org/W2"


async def test_search_retries_once_after_invalid_llm_reply():
    openalex = FakeOpenAlex([candidate("W1", 10)])
    llm = ScriptedLLM(["sorry, no JSON here", '{"papers": [{"id": "W1", "summary": "ok"}]}'])

    result = await PaperSearch(openalex, llm).search("graphs", today=date(2026, 10, 23))

    assert len(llm.prompts) == 2
    assert result.papers[0].summary == "ok"


async def test_search_raises_when_llm_fails_twice():
    openalex = FakeOpenAlex([candidate("W1", 10)])
    llm = ScriptedLLM(["bad", "still bad"])

    with pytest.raises(InvalidSelectionError):
        await PaperSearch(openalex, llm).search("graphs", today=date(2026, 10, 23))


async def test_search_raises_when_no_candidates_have_abstracts():
    openalex = FakeOpenAlex([candidate("W1", 10, abstract="")])
    with pytest.raises(NoPapersFoundError):
        await PaperSearch(openalex, ScriptedLLM([])).search("graphs", today=date(2026, 10, 23))
