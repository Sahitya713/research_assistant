from datetime import date

import pytest

from app.ranking import (
    Candidate,
    InvalidSelectionError,
    build_selection_prompt,
    date_window,
    parse_selection,
    rebuild_abstract,
    select_candidates,
)


def make_candidate(paper_id: str, citations: int, abstract: str = "An abstract.") -> Candidate:
    return Candidate(
        id=paper_id,
        title=f"Paper {paper_id}",
        authors=["Ada Lovelace"],
        year=2025,
        publication_date="2025-01-01",
        citations=citations,
        abstract=abstract,
        url=f"https://doi.org/{paper_id}",
    )


def test_date_window_covers_four_years_before_today():
    assert date_window(date(2026, 10, 23)) == (date(2022, 10, 23), date(2026, 10, 23))


def test_date_window_handles_leap_day():
    start, end = date_window(date(2028, 2, 29))
    assert start == date(2024, 2, 29)
    assert end == date(2028, 2, 29)

    start, _ = date_window(date(2024, 2, 29), years=1)
    assert start == date(2023, 2, 28)


def test_rebuild_abstract_orders_words_by_position():
    index = {"graphs": [2], "Deep": [0], "learning": [1, 4], "for": [3]}
    assert rebuild_abstract(index) == "Deep learning graphs for learning"


def test_rebuild_abstract_returns_empty_for_missing_index():
    assert rebuild_abstract(None) == ""
    assert rebuild_abstract({}) == ""


def test_select_candidates_drops_missing_abstracts_and_sorts_by_citations():
    candidates = [
        make_candidate("low", citations=3),
        make_candidate("no-abstract", citations=999, abstract=""),
        make_candidate("high", citations=50),
        make_candidate("mid", citations=10),
    ]
    selected = select_candidates(candidates)
    assert [c.id for c in selected] == ["high", "mid", "low"]


def test_select_candidates_respects_pool_size():
    candidates = [make_candidate(f"p{i}", citations=i) for i in range(10)]
    selected = select_candidates(candidates, pool_size=3)
    assert [c.id for c in selected] == ["p9", "p8", "p7"]


def test_build_selection_prompt_includes_topic_and_every_candidate():
    candidates = [make_candidate("W1", citations=5), make_candidate("W2", citations=2)]
    prompt = build_selection_prompt("quantum error correction", candidates, max_papers=4)
    assert "Research topic: quantum error correction" in prompt
    assert "Choose the 4 papers" in prompt
    assert "id: W1" in prompt and "id: W2" in prompt


def test_parse_selection_accepts_valid_json():
    reply = '{"papers": [{"id": "W1", "summary": " Key finding. "}]}'
    selections = parse_selection(reply, {"W1", "W2"})
    assert [(s.id, s.summary) for s in selections] == [("W1", "Key finding.")]


def test_parse_selection_strips_markdown_fences():
    reply = '```json\n{"papers": [{"id": "W1", "summary": "Done."}]}\n```'
    selections = parse_selection(reply, {"W1"})
    assert selections[0].id == "W1"


def test_parse_selection_drops_unknown_and_duplicate_ids():
    reply = (
        '{"papers": ['
        '{"id": "ghost", "summary": "x"},'
        '{"id": "W1", "summary": "first"},'
        '{"id": "W1", "summary": "again"},'
        '{"id": "W2", "summary": "second"}'
        "]}"
    )
    selections = parse_selection(reply, {"W1", "W2"})
    assert [s.id for s in selections] == ["W1", "W2"]
    assert selections[0].summary == "first"


def test_parse_selection_caps_at_max_papers():
    ids = {f"W{i}" for i in range(6)}
    reply = '{"papers": [' + ",".join(f'{{"id": "W{i}", "summary": "s"}}' for i in range(6)) + "]}"
    assert len(parse_selection(reply, ids, max_papers=4)) == 4


@pytest.mark.parametrize(
    "reply",
    [
        "not json at all",
        '{"something": "else"}',
        '{"papers": [{"id": "ghost", "summary": "x"}]}',
        '{"papers": [{"id": "W1", "summary": 42}]}',
    ],
)
def test_parse_selection_rejects_unusable_replies(reply):
    with pytest.raises(InvalidSelectionError):
        parse_selection(reply, {"W1"})
