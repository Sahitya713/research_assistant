from datetime import date

from pydantic import BaseModel


class PaperOut(BaseModel):
    id: str
    title: str
    authors: list[str]
    year: int
    summary: str
    url: str


class SearchResponse(BaseModel):
    topic: str
    from_date: date
    to_date: date
    papers: list[PaperOut]
