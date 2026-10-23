from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.llm import LLMError
from app.main import create_app, get_paper_search, get_today
from app.openalex import OpenAlexError
from app.service import NoPapersFoundError, Paper, SearchResult


class StubSearch:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.seen: list[tuple[str, date]] = []

    async def search(self, topic: str, today: date) -> SearchResult:
        self.seen.append((topic, today))
        if self.error:
            raise self.error
        return self.result


def sample_result() -> SearchResult:
    papers = [
        Paper(
            id=f"https://openalex.org/W{i}",
            title=f"Paper {i}",
            authors=["Ada Lovelace"],
            year=2025,
            summary=f"Summary {i}",
            url=f"https://doi.org/10.1/{i}",
        )
        for i in range(4)
    ]
    return SearchResult(topic="graphs", from_date=date(2022, 10, 23), to_date=date(2026, 10, 23), papers=papers)


@pytest.fixture
def make_client():
    clients: list[TestClient] = []

    def build(stub: StubSearch, today: date = date(2026, 10, 23)) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_paper_search] = lambda: stub
        app.dependency_overrides[get_today] = lambda: today
        client = TestClient(app)
        clients.append(client)
        return client

    yield build
    for client in clients:
        client.close()


def test_health_endpoint(make_client):
    response = make_client(StubSearch()).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_returns_four_papers_in_expected_shape(make_client):
    stub = StubSearch(result=sample_result())
    response = make_client(stub).get("/api/search", params={"topic": "  graphs  "})

    assert response.status_code == 200
    body = response.json()
    assert body["topic"] == "graphs"
    assert body["from_date"] == "2022-10-23"
    assert body["to_date"] == "2026-10-23"
    assert len(body["papers"]) == 4
    assert set(body["papers"][0]) == {"id", "title", "authors", "year", "summary", "url"}
    assert stub.seen == [("graphs", date(2026, 10, 23))]


def test_search_uses_today_for_window(make_client):
    stub = StubSearch(result=sample_result())
    make_client(stub, today=date(2030, 5, 1)).get("/api/search", params={"topic": "graphs"})
    assert stub.seen == [("graphs", date(2030, 5, 1))]


@pytest.mark.parametrize("topic", ["", "a", " ", "x" * 201])
def test_search_rejects_invalid_topics(make_client, topic):
    response = make_client(StubSearch(result=sample_result())).get("/api/search", params={"topic": topic})
    assert response.status_code == 422


def test_search_returns_404_when_no_papers(make_client):
    stub = StubSearch(error=NoPapersFoundError("none"))
    response = make_client(stub).get("/api/search", params={"topic": "graphs"})
    assert response.status_code == 404


@pytest.mark.parametrize("error", [OpenAlexError("down"), LLMError("bad key")])
def test_search_returns_502_for_upstream_failures(make_client, error):
    stub = StubSearch(error=error)
    response = make_client(stub).get("/api/search", params={"topic": "graphs"})
    assert response.status_code == 502
    assert response.json()["detail"] == str(error)

