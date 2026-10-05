from __future__ import annotations

from app.config import FJALORTH_BASE
from app.htmlutil import examples_from_em, inner_text, soup
from app.http import request_get, word_url
from app.models import Sense, SourceEntry, SourceResult

TITLE = "Fjalorth.com"
HOMEPAGE = FJALORTH_BASE
LICENSE = "fjalorth.com"


async def lookup(word: str) -> SourceResult:
    url = word_url(FJALORTH_BASE, word)
    try:
        response = await request_get(url)
    except Exception as exc:
        return SourceResult(
            source="fjalorth",
            title=TITLE,
            homepage=HOMEPAGE,
            license=LICENSE,
            url=url,
            error=f"Could not reach fjalorth.com ({exc.__class__.__name__})",
        )

    if response.status_code == 404:
        return SourceResult(
            source="fjalorth",
            title=TITLE,
            homepage=HOMEPAGE,
            license=LICENSE,
            url=str(response.url),
            found=False,
        )

    if response.status_code >= 400:
        return SourceResult(
            source="fjalorth",
            title=TITLE,
            homepage=HOMEPAGE,
            license=LICENSE,
            url=str(response.url),
            error=f"fjalorth.com returned HTTP {response.status_code}",
        )

    entries = parse_entry(response.text)
    return SourceResult(
        source="fjalorth",
        title=TITLE,
        homepage=HOMEPAGE,
        license=LICENSE,
        url=str(response.url),
        found=bool(entries),
        entries=entries,
    )


def parse_entry(html: str) -> list[SourceEntry]:
    page = soup(html)
    section = page.select_one("section.word-section")
    if section is None:
        return []
    heading = inner_text(section.select_one("h2.word"))
    if "nuk u gjend" in heading.casefold():
        return []

    definition = section.select_one(".definition")
    if definition is None:
        return []

    head = inner_text(definition.find("strong"))
    pos = inner_text(definition.find("em"))
    senses: list[Sense] = []
    for i, item in enumerate(definition.select("ol > li"), start=1):
        gloss, examples = examples_from_em(item)
        senses.append(Sense(number=i, gloss=gloss, examples=examples))

    translations: dict[str, list[str]] = {}
    trans_block = page.select_one(".translations")
    if trans_block is not None:
        line = inner_text(trans_block)
        if ":" in line:
            _, value = line.split(":", 1)
            value = value.strip()
            if value:
                translations["en"] = [value]

    if not senses:
        return []
    return [
        SourceEntry(
            headword=head or heading.replace("Fjala:", "").strip(),
            part_of_speech=[pos] if pos else [],
            senses=senses,
            translations=translations,
            exact_match=True,
        )
    ]
