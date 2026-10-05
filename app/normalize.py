from __future__ import annotations

import re
import unicodedata

from app.config import MAX_WORD_LENGTH

_ALLOWED_MARKS = {"-", "'", "’", "ʼ", " ", "."}


def normalize_word(raw: str) -> str:
    text = unicodedata.normalize("NFC", raw or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def is_valid_word(word: str) -> bool:
    if not word or len(word) > MAX_WORD_LENGTH:
        return False
    letters = 0
    for ch in word:
        if ch.isalpha():
            letters += 1
            continue
        if ch in _ALLOWED_MARKS:
            continue
        return False
    return letters >= 1


def word_key(word: str) -> str:
    return normalize_word(word).casefold()


_DIACRITIC_FOLD = str.maketrans(
    {
        "ë": "e",
        "Ë": "E",
        "ç": "c",
        "Ç": "C",
        "á": "a",
        "à": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ý": "y",
    }
)


def lookup_variants(word: str) -> list[str]:
    nfc = normalize_word(word)
    folded = nfc.translate(_DIACRITIC_FOLD)
    variants = [nfc]
    if folded != nfc:
        variants.append(folded)
    lowered = nfc.casefold()
    if lowered not in {item.casefold() for item in variants}:
        variants.append(lowered)
    return variants
