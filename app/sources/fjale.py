from __future__ import annotations

import re

from app.config import FJALE_BASE
from app.htmlutil import inner_text, soup, unique
from app.http import request_get, word_url
from app.models import Sense, SourceEntry, SourceResult

TITLE = "FJALË"
HOMEPAGE = FJALE_BASE
LICENSE = "fjale.al"

LABEL_RE = re.compile(
    r"^(zakon|keq|bised|libr|fig|mjek|fol|sh|kj|v|përh|rrall|ngusht|"
    r"gjeog|bot|zool|kim|mat|fiz|muz|fet|hist|bujq|usht|iron|poh|moh)\b",
    re.IGNORECASE,
)
LEADING_NUMBER = re.compile(r"^\d+\.\s*")


async def lookup(word: str) -> SourceResult:
    url = word_url(FJALE_BASE, word)
    try:
        response = await request_get(url)
    except Exception as exc:
        return SourceResult(
            source="fjale",
            title=TITLE,
            homepage=HOMEPAGE,
            license=LICENSE,
            url=url,
            error=f"Could not reach fjale.al ({exc.__class__.__name__})",
        )

    result_url = str(response.url)
    if response.status_code == 404:
        suggestion = _did_you_mean(response.text)
        related = [suggestion] if suggestion else []
        return SourceResult(
            source="fjale",
            title=TITLE,
            homepage=HOMEPAGE,
            license=LICENSE,
            url=result_url,
            found=False,
            entries=(
                [SourceEntry(headword=word, related=related, exact_match=False)]
                if related
                else []
            ),
        )

    if response.status_code >= 400:
        return SourceResult(
            source="fjale",
            title=TITLE,
            homepage=HOMEPAGE,
            license=LICENSE,
            url=result_url,
            error=f"fjale.al returned HTTP {response.status_code}",
        )

    entries = parse_entry(response.text)
    return SourceResult(
        source="fjale",
        title=TITLE,
        homepage=HOMEPAGE,
        license=LICENSE,
        url=result_url,
        found=bool(entries),
        entries=entries,
    )


def parse_entry(html: str) -> list[SourceEntry]:
    page = soup(html)
    block = page.select_one("#e.def")
    if block is None:
        return []

    body = inner_text(block)
    lowered = body.casefold()
    if "nuk ekziston" in lowered or "kemi mbetur pa fjalë" in lowered:
        return []
    if "mos e kishe llafin" in lowered:
        hint = block.select_one("h3 a")
        related = [inner_text(hint)] if hint is not None else []
        return [SourceEntry(headword="", related=related, exact_match=False)] if related else []

    head = block.find(["strong", "b"])
    pos = ""
    if head is not None:
        sibling = head.find_next_sibling("em")
        pos = inner_text(sibling) if sibling is not None else ""
        if not pos and head.parent is not None:
            leftover = inner_text(head.parent).replace(inner_text(head), "", 1).strip(" .,;")
            if leftover and len(leftover) <= 16:
                pos = leftover
    headword = inner_text(head)
    slug = str(block.get("data-slug") or headword).strip()

    senses: list[Sense] = []
    items = block.select("ol > li") or block.select("ul > li")
    for i, item in enumerate(items, start=1):
        gloss, examples, labels = _sense_parts(item)
        if gloss or examples:
            senses.append(Sense(number=i, gloss=gloss or (examples[0] if examples else ""), examples=examples, labels=labels))

    related = unique([inner_text(a) for a in block.select(".rel a")])
    if not senses and not headword:
        return []
    if not senses and body:
        senses = [Sense(gloss=body)]

    return [
        SourceEntry(
            headword=headword or slug,
            lemma=slug or None,
            part_of_speech=[pos] if pos else [],
            senses=senses,
            related=related,
            exact_match=True,
        )
    ]


def _sense_parts(item) -> tuple[str, list[str], list[str]]:
    labels: list[str] = []
    examples: list[str] = []
    for em in list(item.find_all("em")):
        text = inner_text(em)
        if not text:
            em.extract()
            continue
        if LABEL_RE.search(text) and len(text) <= 48:
            labels.append(text)
        else:
            examples.append(text)
        em.extract()
    gloss = LEADING_NUMBER.sub("", inner_text(item)).strip()
    return gloss, unique(examples), unique(labels)


def _did_you_mean(html: str) -> str | None:
    page = soup(html)
    hint = page.select_one("#e.def h3 a")
    if hint is None:
        return None
    text = inner_text(hint)
    return text or None
