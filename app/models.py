from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SourceId = Literal["fjale", "fjalorthi", "fjalorth", "wiktionary_en", "wiktionary_sq"]

ALL_SOURCES: tuple[SourceId, ...] = (
    "fjale",
    "fjalorthi",
    "fjalorth",
    "wiktionary_en",
    "wiktionary_sq",
)


class Sense(BaseModel):
    number: int | None = None
    gloss: str
    examples: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)


class SourceEntry(BaseModel):
    headword: str
    lemma: str | None = None
    part_of_speech: list[str] = Field(default_factory=list)
    senses: list[Sense] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    translations: dict[str, list[str]] = Field(default_factory=dict)
    inflections: list[str] = Field(default_factory=list)
    exact_match: bool = True
    raw_definition: str | None = None


class SourceResult(BaseModel):
    source: SourceId
    title: str
    homepage: str
    license: str
    url: str | None = None
    found: bool = False
    error: str | None = None
    entries: list[SourceEntry] = Field(default_factory=list)


class MergedEntry(BaseModel):
    headword: str
    pos: list[str] = Field(default_factory=list)
    part_of_speech: list[str] = Field(default_factory=list)
    senses: list[Sense] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    translations: dict[str, list[str]] = Field(default_factory=dict)


class Attribution(BaseModel):
    notice: str
    licenses: list[str] = Field(default_factory=list)
    cited_urls: list[str] = Field(default_factory=list)


class LookupResponse(BaseModel):
    query: str
    canonical: str | None = None
    found: bool
    merged: MergedEntry | None = None
    sources: list[SourceResult]
    suggestions: list[str] = Field(default_factory=list)
    attribution: Attribution | None = None
    cached: bool = False


class ApiIndex(BaseModel):
    name: str
    version: str
    docs: str
    openapi: str
    no_api_key: bool = True
    rate_limit: str
    endpoints: dict[str, str]
    example: str


class HealthResponse(BaseModel):
    status: str
    version: str
    sources: dict[str, str]


class ErrorBody(BaseModel):
    error: str
    detail: str
    docs: str = "/docs"
    suggestions: list[str] = Field(default_factory=list)


class SuggestResponse(BaseModel):
    query: str
    suggestions: list[str]


class Quote(BaseModel):
    author: str | None = None
    title: str | None = None
    excerpt: str


class QuotesResponse(BaseModel):
    query: str
    quotes: list[Quote]


class WordOfTheDayResponse(BaseModel):
    word: str
    definition: str | None = None
    source: str = "fjalorthi"
    url: str | None = None
    lookup: LookupResponse | None = None


class TrendingWord(BaseModel):
    word: str
    views: int | None = None


class TrendingResponse(BaseModel):
    words: list[TrendingWord]


class SourceInfo(BaseModel):
    id: SourceId
    title: str
    homepage: str
    license: str
    access: str
    fields: list[str]


def unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if not key:
            continue
        folded = key.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        out.append(key)
    return out
