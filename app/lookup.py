from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence

from app.cache import cache
from app.models import (
    ALL_SOURCES,
    Attribution,
    LookupResponse,
    MergedEntry,
    Sense,
    SourceId,
    SourceResult,
    unique_keep_order,
)
from app.normalize import lookup_variants, normalize_word, word_key
from app.pos import canonical_pos
from app.sources import fjale, fjalorth, fjalorthi, wiktionary

Fetcher = Callable[[str], Awaitable[SourceResult]]


def _fetchers() -> dict[SourceId, Fetcher]:
    return {
        "fjale": fjale.lookup,
        "fjalorthi": fjalorthi.lookup,
        "fjalorth": fjalorth.lookup,
        "wiktionary_en": wiktionary.lookup_en,
        "wiktionary_sq": wiktionary.lookup_sq,
    }


async def lookup_word(word: str, sources: Sequence[SourceId] | None = None) -> LookupResponse:
    query = normalize_word(word)
    wanted: tuple[SourceId, ...] = tuple(sources) if sources else ALL_SOURCES
    cache_id = f"lookup:{word_key(query)}:{','.join(wanted)}"
    cached = cache.get(cache_id)
    if isinstance(cached, LookupResponse):
        return cached.model_copy(update={"cached": True})

    fetchers = _fetchers()
    tasks = [fetchers[source](query) for source in wanted]
    raw = await asyncio.gather(*tasks, return_exceptions=True)
    results: list[SourceResult] = []
    for source, item in zip(wanted, raw, strict=True):
        if isinstance(item, SourceResult):
            results.append(item)
            continue
        message = item.__class__.__name__ if isinstance(item, BaseException) else "unknown error"
        meta = _fallback_meta(source)
        results.append(
            SourceResult(
                source=source,
                title=meta[0],
                homepage=meta[1],
                license=meta[2],
                error=f"Lookup failed ({message})",
            )
        )

    results = await _fill_misses_with_variants(query, wanted, fetchers, results)
    found_entries = _primary_entries(results, query)
    canonical = found_entries[0].headword if found_entries else None
    merged = merge_entries(canonical or query, found_entries) if found_entries else None
    suggestions = _suggestions(results, query)
    response = LookupResponse(
        query=query,
        canonical=canonical,
        found=bool(found_entries),
        merged=merged,
        sources=results,
        suggestions=suggestions,
        attribution=_attribution(results),
        cached=False,
    )
    stored = cache.set(cache_id, response)
    stored.cached = False
    return stored


def _primary_entries(results: list[SourceResult], query: str) -> list:
    exact = [entry for result in results if result.found for entry in result.entries if entry.exact_match]
    fuzzy = [entry for result in results if result.found for entry in result.entries if not entry.exact_match]
    pool = exact or fuzzy
    if not pool:
        return []
    folded = query.casefold()
    matched = [entry for entry in pool if entry.headword.casefold() == folded]
    return matched or pool[:1]


def merge_entries(headword: str, entries: list) -> MergedEntry:
    pos: list[str] = []
    senses: list[Sense] = []
    synonyms: list[str] = []
    antonyms: list[str] = []
    related: list[str] = []
    translations: dict[str, list[str]] = {}
    seen_glosses: set[str] = set()

    ranked = sorted(entries, key=lambda e: -sum(len(s.gloss) for s in e.senses))
    for entry in ranked:
        pos.extend(entry.part_of_speech)
        synonyms.extend(entry.synonyms)
        antonyms.extend(entry.antonyms)
        related.extend(entry.related)
        for lang, words in entry.translations.items():
            translations.setdefault(lang, []).extend(words)
        for sense in entry.senses:
            key = sense.gloss.casefold()
            if key in seen_glosses:
                continue
            seen_glosses.add(key)
            senses.append(sense)

    numbered: list[Sense] = []
    for i, sense in enumerate(senses, start=1):
        numbered.append(
            Sense(
                number=i,
                gloss=sense.gloss,
                examples=sense.examples,
                labels=sense.labels,
            )
        )
    return MergedEntry(
        headword=headword,
        pos=canonical_pos(pos),
        part_of_speech=unique_keep_order(pos),
        senses=numbered,
        synonyms=unique_keep_order(synonyms),
        antonyms=unique_keep_order(antonyms),
        related=unique_keep_order(related),
        translations={lang: unique_keep_order(words) for lang, words in translations.items()},
    )


async def _fill_misses_with_variants(
    query: str,
    wanted: tuple[SourceId, ...],
    fetchers: dict[SourceId, Fetcher],
    results: list[SourceResult],
) -> list[SourceResult]:
    variants = [item for item in lookup_variants(query) if item.casefold() != query.casefold()]
    if not variants:
        return results
    retries: list[tuple[int, SourceId, str]] = []
    for index, (source, result) in enumerate(zip(wanted, results, strict=True)):
        if result.found or result.error:
            continue
        retries.append((index, source, variants[0]))
    if not retries:
        return results
    retry_raw = await asyncio.gather(
        *[fetchers[source](variant) for _, source, variant in retries],
        return_exceptions=True,
    )
    for (index, _source, _variant), item in zip(retries, retry_raw, strict=True):
        if isinstance(item, SourceResult) and item.found:
            results[index] = item
    return results


def _attribution(results: list[SourceResult]) -> Attribution:
    urls = unique_keep_order([item.url or item.homepage for item in results if item.found])
    licenses = unique_keep_order([item.license for item in results if item.found])
    return Attribution(
        notice="Cite the source URLs. Wiktionary text is CC BY-SA 4.0.",
        licenses=licenses,
        cited_urls=urls,
    )


def _suggestions(results: list[SourceResult], query: str) -> list[str]:
    words: list[str] = []
    for result in results:
        for entry in result.entries:
            words.append(entry.headword)
            words.extend(entry.related)
            words.extend(entry.synonyms)
    folded = query.casefold()
    return unique_keep_order([w for w in words if w.casefold() != folded])[:12]


def _fallback_meta(source: SourceId) -> tuple[str, str, str]:
    mapping = {
        "fjale": ("FJALË", "https://fjale.al/", "fjale.al"),
        "fjalorthi": ("Fjalorthi", "https://fjalorthi.com/", "fjalorthi.com"),
        "fjalorth": ("Fjalorth.com", "https://www.fjalorth.com/", "fjalorth.com"),
        "wiktionary_en": ("English Wiktionary", "https://en.wiktionary.org/", "CC BY-SA 4.0"),
        "wiktionary_sq": ("Wiktionary shqip", "https://sq.wiktionary.org/", "CC BY-SA 4.0"),
    }
    return mapping[source]
