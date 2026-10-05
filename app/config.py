from __future__ import annotations

USER_AGENT = "FjalorShqipAPI/0.2"

REQUEST_TIMEOUT_SECONDS = 12.0
CACHE_TTL_SECONDS = 60 * 45
CACHE_MAX_ENTRIES = 2048
MAX_WORD_LENGTH = 80
UPSTREAM_RETRIES = 3
WIKTIONARY_MIN_INTERVAL = 0.25
INBOUND_RATE_LIMIT = 60
INBOUND_RATE_WINDOW = 60.0

FJALE_BASE = "https://fjale.al"
FJALORTHI_BASE = "https://fjalorthi.com"
FJALORTH_BASE = "https://www.fjalorth.com"
WIKTIONARY_EN = "https://en.wiktionary.org"
WIKTIONARY_SQ = "https://sq.wiktionary.org"
TRENDING_URL = (
    "https://fjalorthi-trending-top-words-bucket-prod.s3.eu-central-1.amazonaws.com/"
    "top_ga_words.json"
)
