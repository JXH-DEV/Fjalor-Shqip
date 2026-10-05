from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag

SENSE_SPLIT = re.compile(r"(?:(?<=^)|(?<=[\s;]))(\d+)\.\s+")
WHITESPACE = re.compile(r"\s+")


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def collapse(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip()


def inner_text(node: Tag | NavigableString | None) -> str:
    if node is None:
        return ""
    if isinstance(node, NavigableString):
        return collapse(str(node))
    return collapse(node.get_text(" ", strip=True))


def strip_html(html: str) -> str:
    if not html:
        return ""
    return collapse(soup(html).get_text(" ", strip=True))


def fjalorthi_to_text(html: str) -> tuple[str, list[str]]:
    parsed = soup(f"<div>{html}</div>")
    labels: list[str] = []
    for span in parsed.select("span.SHRT"):
        label = collapse(span.get_text(" ", strip=True)).rstrip(";")
        if label:
            labels.append(label)
        span.replace_with(NavigableString(f" ({label}) " if label else " "))
    for link in parsed.select("a"):
        link.replace_with(NavigableString(link.get_text(" ", strip=True)))
    return collapse(parsed.get_text(" ", strip=True)), unique(labels)


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = collapse(item)
        if not key:
            continue
        folded = key.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        out.append(key)
    return out


def split_numbered_senses(text: str) -> list[tuple[int | None, str]]:
    text = collapse(text)
    if not text:
        return []
    parts = SENSE_SPLIT.split(text)
    if len(parts) == 1:
        return [(None, text)]
    senses: list[tuple[int | None, str]] = []
    preamble = parts[0].strip(" ;,")
    i = 1
    while i < len(parts):
        try:
            number = int(parts[i])
        except ValueError:
            i += 1
            continue
        gloss = parts[i + 1].strip(" ;") if i + 1 < len(parts) else ""
        if gloss:
            senses.append((number, gloss))
        i += 2
    if not senses and preamble:
        return [(None, preamble)]
    return senses


def examples_from_em(node: Tag) -> tuple[str, list[str]]:
    examples: list[str] = []
    clone = soup(str(node))
    root = clone.find()
    if root is None:
        return inner_text(node), []
    for em in root.find_all("em"):
        sample = inner_text(em)
        if sample:
            examples.append(sample)
        em.decompose()
    return inner_text(root), unique(examples)
