from __future__ import annotations

import re

from app.config import WIKTIONARY_EN, WIKTIONARY_SQ
from app.htmlutil import inner_text, soup, strip_html, unique
from app.http import request_get, word_url
from app.models import Sense, SourceEntry, SourceId, SourceResult

POS_HEADING = re.compile(
    r"^(Emër|Folje|Mbiemër|Ndajfolje|Përemër|Lidhëz|Parafjalë|Pasthirrmë|Pjesëz|Numëror)\b",
    re.IGNORECASE,
)


async def lookup_en(word: str) -> SourceResult:
    url = word_url(WIKTIONARY_EN, "api", "rest_v1", "page", "definition", word)
    homepage = word_url(WIKTIONARY_EN, "wiki", word)
    try:
        response = await request_get(url, headers={"Accept": "application/json"})
    except Exception as exc:
        return _error("wiktionary_en", url, f"Could not reach English Wiktionary ({exc.__class__.__name__})")

    if response.status_code == 404:
        return SourceResult(
            source="wiktionary_en",
            title="English Wiktionary",
            homepage=WIKTIONARY_EN,
            license="CC BY-SA 4.0",
            url=homepage,
            found=False,
        )
    if response.status_code >= 400:
        return _error("wiktionary_en", url, f"English Wiktionary returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except Exception:
        return _error("wiktionary_en", url, "English Wiktionary returned a non-JSON body")

    entries = parse_en_definitions(word, payload)
    return SourceResult(
        source="wiktionary_en",
        title="English Wiktionary",
        homepage=WIKTIONARY_EN,
        license="CC BY-SA 4.0",
        url=homepage,
        found=bool(entries),
        entries=entries,
    )


def parse_en_definitions(word: str, payload: dict) -> list[SourceEntry]:
    albanian = payload.get("sq") or []
    entries: list[SourceEntry] = []
    for item in albanian:
        senses: list[Sense] = []
        for i, definition in enumerate(item.get("definitions") or [], start=1):
            gloss = strip_html(definition.get("definition") or "")
            examples = [strip_html(ex) for ex in definition.get("examples") or [] if ex]
            if gloss:
                senses.append(Sense(number=i, gloss=gloss, examples=examples))
        pos = item.get("partOfSpeech")
        if not senses:
            continue
        entries.append(
            SourceEntry(
                headword=word,
                part_of_speech=[pos] if pos else [],
                senses=senses,
                translations={"en": [s.gloss for s in senses]},
                exact_match=True,
            )
        )
    return entries


async def lookup_sq(word: str) -> SourceResult:
    api = f"{WIKTIONARY_SQ}/w/api.php"
    homepage = word_url(WIKTIONARY_SQ, "wiki", word)
    try:
        response = await request_get(
            api,
            params={
                "action": "parse",
                "page": word,
                "prop": "text",
                "format": "json",
                "redirects": "1",
                "disablelimitreport": "1",
            },
        )
    except Exception as exc:
        return _error("wiktionary_sq", homepage, f"Could not reach Albanian Wiktionary ({exc.__class__.__name__})")

    if response.status_code >= 400:
        return _error("wiktionary_sq", homepage, f"Albanian Wiktionary returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except Exception:
        return _error("wiktionary_sq", homepage, "Albanian Wiktionary returned a non-JSON body")

    if "error" in payload:
        return SourceResult(
            source="wiktionary_sq",
            title="Wiktionary shqip",
            homepage=WIKTIONARY_SQ,
            license="CC BY-SA 4.0",
            url=homepage,
            found=False,
        )

    html = ((payload.get("parse") or {}).get("text") or {}).get("*") or ""
    title = (payload.get("parse") or {}).get("title") or word
    entries = parse_sq_html(title, html)
    return SourceResult(
        source="wiktionary_sq",
        title="Wiktionary shqip",
        homepage=WIKTIONARY_SQ,
        license="CC BY-SA 4.0",
        url=homepage,
        found=bool(entries),
        entries=entries,
    )


def parse_sq_html(word: str, html: str) -> list[SourceEntry]:
    page = soup(html)
    entries: list[SourceEntry] = []
    current_pos: str | None = None
    for node in page.select(".mw-parser-output > *"):
        heading = node.select_one("h2, h3, h4")
        if heading is not None:
            title = inner_text(heading)
            if POS_HEADING.match(title):
                current_pos = title.split()[0]
            continue
        if node.name == "ol" and current_pos:
            senses: list[Sense] = []
            for i, item in enumerate(node.find_all("li", recursive=False), start=1):
                gloss = inner_text(item)
                if gloss:
                    senses.append(Sense(number=i, gloss=gloss))
            if senses:
                entries.append(
                    SourceEntry(
                        headword=word,
                        part_of_speech=[current_pos] if current_pos else [],
                        senses=senses,
                        exact_match=True,
                    )
                )
    if entries:
        return entries
    first_ol = page.select_one(".mw-parser-output ol")
    if first_ol is None:
        return []
    senses = []
    for i, item in enumerate(first_ol.find_all("li", recursive=False), start=1):
        gloss = inner_text(item)
        if gloss:
            senses.append(Sense(number=i, gloss=gloss))
    if not senses:
        return []
    return [SourceEntry(headword=word, senses=senses, exact_match=True)]


async def suggest(query: str, limit: int = 8) -> list[str]:
    response = await request_get(
        f"{WIKTIONARY_SQ}/w/api.php",
        params={
            "action": "opensearch",
            "search": query,
            "limit": str(limit),
            "namespace": "0",
            "format": "json",
        },
    )
    if response.status_code >= 400:
        return []
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    return unique([str(item) for item in payload[1]])


def _error(source: SourceId, url: str, message: str) -> SourceResult:
    titles = {
        "wiktionary_en": "English Wiktionary",
        "wiktionary_sq": "Wiktionary shqip",
    }
    homes = {
        "wiktionary_en": WIKTIONARY_EN,
        "wiktionary_sq": WIKTIONARY_SQ,
    }
    return SourceResult(
        source=source,
        title=titles[source],
        homepage=homes[source],
        license="CC BY-SA 4.0",
        url=url,
        error=message,
    )
