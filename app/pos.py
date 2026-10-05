from __future__ import annotations

from app.models import unique_keep_order

_CANONICAL = (
    ("emër", "noun"),
    ("emra", "noun"),
    ("noun", "noun"),
    ("folje", "verb"),
    ("verb", "verb"),
    ("mbiemër", "adjective"),
    ("adjective", "adjective"),
    ("ndajfolje", "adverb"),
    ("adverb", "adverb"),
    ("përemër", "pronoun"),
    ("pronoun", "pronoun"),
    ("lidhëz", "conjunction"),
    ("conjunction", "conjunction"),
    ("parafjalë", "preposition"),
    ("preposition", "preposition"),
    ("pasthirrmë", "interjection"),
    ("interjection", "interjection"),
    ("numëror", "numeral"),
    ("numeral", "numeral"),
    ("pjesore", "participle"),
    ("participle", "participle"),
)

_SHORT = {
    "f.": "noun",
    "f": "noun",
    "m.": "noun",
    "m": "noun",
    "sh.": "noun",
    "mb.": "adjective",
    "mb": "adjective",
    "ndajf.": "adverb",
    "ndajfolje": "adverb",
}


def canonical_pos(labels: list[str]) -> list[str]:
    found: list[str] = []
    for label in labels:
        text = (label or "").strip()
        if not text:
            continue
        lowered = text.casefold().rstrip(".")
        if lowered in _SHORT:
            found.append(_SHORT[lowered])
            continue
        if text.casefold() in _SHORT:
            found.append(_SHORT[text.casefold()])
            continue
        for needle, code in _CANONICAL:
            if needle in text.casefold():
                found.append(code)
                break
    return unique_keep_order(found)
