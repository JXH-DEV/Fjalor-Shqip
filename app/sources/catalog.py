from __future__ import annotations

from app.models import SourceInfo

SOURCES: list[SourceInfo] = [
    SourceInfo(
        id="fjale",
        title="FJALË (fjale.al)",
        homepage="https://fjale.al/",
        license="fjale.al",
        access="HTML pages",
        fields=["senses", "examples", "part_of_speech", "related"],
    ),
    SourceInfo(
        id="fjalorthi",
        title="Fjalorthi (fjalorthi.com)",
        homepage="https://fjalorthi.com/",
        license="fjalorthi.com",
        access="/prod/define JSON",
        fields=["senses", "part_of_speech", "synonyms", "antonyms", "inflections"],
    ),
    SourceInfo(
        id="fjalorth",
        title="Fjalorth.com",
        homepage="https://www.fjalorth.com/",
        license="fjalorth.com",
        access="HTML pages",
        fields=["senses", "examples", "part_of_speech", "translations"],
    ),
    SourceInfo(
        id="wiktionary_en",
        title="English Wiktionary",
        homepage="https://en.wiktionary.org/",
        license="CC BY-SA 4.0",
        access="REST definitions",
        fields=["senses", "part_of_speech", "translations"],
    ),
    SourceInfo(
        id="wiktionary_sq",
        title="Wiktionary shqip",
        homepage="https://sq.wiktionary.org/",
        license="CC BY-SA 4.0",
        access="MediaWiki parse API",
        fields=["senses", "part_of_speech"],
    ),
]
