from __future__ import annotations

from app.cache import cache
from app.models import SuggestResponse, unique_keep_order
from app.normalize import normalize_word, word_key
from app.sources import fjalorthi, wiktionary


async def suggest_words(query: str, limit: int = 8) -> SuggestResponse:
    q = normalize_word(query)
    cache_id = f"suggest:{word_key(q)}:{limit}"
    cached = cache.get(cache_id)
    if isinstance(cached, SuggestResponse):
        return cached

    wiki = await wiktionary.suggest(q, limit=limit)
    extra: list[str] = []
    if len(wiki) < limit:
        defined = await fjalorthi.lookup(q)
        for entry in defined.entries:
            extra.append(entry.headword)
            extra.extend(entry.related)
            extra.extend(entry.inflections)

    suggestions = unique_keep_order([*wiki, *extra])[:limit]
    response = SuggestResponse(query=q, suggestions=suggestions)
    return cache.set(cache_id, response)
