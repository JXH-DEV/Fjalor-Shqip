from __future__ import annotations

from app.config import FJALORTHI_BASE, TRENDING_URL
from app.htmlutil import fjalorthi_to_text, split_numbered_senses, unique
from app.http import request_get, word_url
from app.models import Quote, Sense, SourceEntry, SourceResult, TrendingWord

TITLE = "Fjalorthi"
HOMEPAGE = FJALORTHI_BASE
LICENSE = "fjalorthi.com"


async def lookup(word: str) -> SourceResult:
    url = word_url(FJALORTHI_BASE, "prod", "define", word)
    try:
        response = await request_get(url, headers={"Accept": "application/json"})
    except Exception as exc:
        return SourceResult(
            source="fjalorthi",
            title=TITLE,
            homepage=HOMEPAGE,
            license=LICENSE,
            url=url,
            error=f"Could not reach fjalorthi.com ({exc.__class__.__name__})",
        )

    if response.status_code >= 400:
        return SourceResult(
            source="fjalorthi",
            title=TITLE,
            homepage=HOMEPAGE,
            license=LICENSE,
            url=url,
            error=f"fjalorthi.com returned HTTP {response.status_code}",
        )

    try:
        payload = response.json()
    except Exception:
        return SourceResult(
            source="fjalorthi",
            title=TITLE,
            homepage=HOMEPAGE,
            license=LICENSE,
            url=url,
            error="fjalorthi.com returned a non-JSON body",
        )

    entries = parse_define(payload)
    return SourceResult(
        source="fjalorthi",
        title=TITLE,
        homepage=HOMEPAGE,
        license=LICENSE,
        url=f"{FJALORTHI_BASE}/{word}",
        found=any(e.exact_match for e in entries) or bool(entries),
        entries=entries,
    )


def parse_define(payload: dict) -> list[SourceEntry]:
    exact = payload.get("exactMatches") or []
    fuzzy = payload.get("fuzzyMatches") or []
    entries: list[SourceEntry] = []
    seen: set[tuple[str, str]] = set()
    for raw, exact_match in [(item, True) for item in exact] + [(item, False) for item in fuzzy]:
        entry = _entry_from_match(raw, exact_match=exact_match)
        key = (entry.headword.casefold(), (entry.raw_definition or "")[:80])
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return entries


_POS_HINTS = (
    "emër",
    "folje",
    "mbiemër",
    "ndajfolje",
    "përemër",
    "pjesore",
    "lidhëz",
    "parafjalë",
    "pasthirrmë",
    "numëror",
    "pjesëz",
)


def _split_labels(labels: list[str]) -> tuple[list[str], list[str]]:
    pos: list[str] = []
    extra: list[str] = []
    for label in labels:
        lowered = label.casefold()
        if any(hint in lowered for hint in _POS_HINTS):
            pos.append(label)
        else:
            extra.append(label)
    return unique(pos), unique(extra)


def _entry_from_match(raw: dict, *, exact_match: bool) -> SourceEntry:
    html = raw.get("wordDefinition") or ""
    text, labels = fjalorthi_to_text(html)
    pos, extra = _split_labels(labels)
    numbered = split_numbered_senses(text)
    senses = [Sense(number=n, gloss=g, labels=extra if i == 0 else []) for i, (n, g) in enumerate(numbered)]
    inflections = unique(
        [
            raw.get("word5") or "",
            raw.get("wordOrig") or "",
            *[raw.get(f"wordDer{i}") or "" for i in range(1, 10)],
        ]
    )
    headword = (raw.get("canonicalWord") or raw.get("word") or raw.get("word2") or "").strip()
    return SourceEntry(
        headword=headword,
        lemma=raw.get("word5") or headword,
        part_of_speech=pos,
        senses=senses,
        synonyms=unique(list(raw.get("synonyms") or [])),
        antonyms=unique(list(raw.get("antonyms") or [])),
        inflections=inflections,
        exact_match=bool(raw.get("exactMatch", exact_match)),
        raw_definition=text or None,
    )


async def word_of_the_day() -> dict | None:
    response = await request_get(word_url(FJALORTHI_BASE, "prod", "wordoftheday"))
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not data.get("word"):
        return None
    definition, _ = fjalorthi_to_text(data.get("definition") or "")
    return {"word": data["word"], "definition": definition or None}


async def quotes(word: str) -> list[Quote]:
    response = await request_get(word_url(FJALORTHI_BASE, "prod", "highlight", word))
    if response.status_code >= 400:
        return []
    try:
        payload = response.json()
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    out: list[Quote] = []
    for item in payload:
        fragments = item.get("highlightedFragments") or []
        excerpt = " ".join(fragments).replace("\n", " ").replace("<B>", "").replace("</B>", "")
        excerpt = " ".join(excerpt.split())
        if not excerpt:
            continue
        out.append(
            Quote(
                author=item.get("author"),
                title=item.get("title"),
                excerpt=excerpt,
            )
        )
    return out


async def trending(limit: int = 12) -> list[TrendingWord]:
    response = await request_get(TRENDING_URL)
    response.raise_for_status()
    payload = response.json()
    words: list[TrendingWord] = []
    if not isinstance(payload, list):
        return words
    for item in payload[:limit]:
        word = (item.get("word") or "").strip()
        if not word:
            continue
        views_raw = item.get("uniquePageViews")
        views = int(views_raw) if str(views_raw).isdigit() else None
        words.append(TrendingWord(word=word, views=views))
    return words
