from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import INBOUND_RATE_LIMIT, INBOUND_RATE_WINDOW
from app.http import close_client
from app.lookup import lookup_word
from app.models import (
    ALL_SOURCES,
    ApiIndex,
    ErrorBody,
    HealthResponse,
    LookupResponse,
    QuotesResponse,
    SourceId,
    SourceInfo,
    SuggestResponse,
    TrendingResponse,
    WordOfTheDayResponse,
)
from app.normalize import is_valid_word, normalize_word
from app.ratelimit import inbound_limiter
from app.sources import fjalorthi
from app.sources.catalog import SOURCES
from app.suggest import suggest_words

ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))
VERSION = "0.2.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_client()


app = FastAPI(
    title="Fjalor Shqip API",
    version=VERSION,
    description="Albanian dictionary lookups from fjale.al, Fjalorthi, Fjalorth.com, and Wiktionary. "
    "Use GET /api/v1/lookup?q={word}. Limit 60 requests/minute/IP. Wiktionary: CC BY-SA 4.0.",
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path.startswith("/api/") and path != "/api/v1/health":
            allowed, remaining, retry_after = inbound_limiter.hit(_client_ip(request))
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content=ErrorBody(
                        error="rate_limited",
                        detail=f"Limit is {INBOUND_RATE_LIMIT} requests per {int(INBOUND_RATE_WINDOW)} seconds.",
                    ).model_dump(),
                    headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": str(INBOUND_RATE_LIMIT), "X-RateLimit-Remaining": "0"},
                )
        else:
            remaining = INBOUND_RATE_LIMIT
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(INBOUND_RATE_LIMIT)
        if path.startswith("/api/"):
            response.headers.setdefault("X-RateLimit-Remaining", str(max(remaining, 0)))
            if request.method == "GET" and path != "/api/v1/health":
                response.headers.setdefault("Cache-Control", "public, max-age=120")
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


app.add_middleware(RateLimitMiddleware)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    code = "http_error"
    if exc.status_code == 400:
        code = "bad_request"
    elif exc.status_code == 404:
        code = "not_found"
    elif exc.status_code == 429:
        code = "rate_limited"
    elif exc.status_code >= 500:
        code = "upstream_error"
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorBody(error=code, detail=detail).model_dump(),
        headers=dict(exc.headers or {}),
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorBody(error="invalid_request", detail=str(exc.errors()[0]["msg"]) if exc.errors() else "Invalid request").model_dump(),
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request) -> HTMLResponse:
    origin = str(request.base_url).rstrip("/")
    return templates.TemplateResponse(
        request,
        "index.html",
        {"sources": SOURCES, "origin": origin, "version": VERSION, "rate_limit": INBOUND_RATE_LIMIT},
    )


@app.get("/api/v1", response_model=ApiIndex, tags=["meta"])
async def api_index(request: Request) -> ApiIndex:
    origin = str(request.base_url).rstrip("/")
    return ApiIndex(
        name="Fjalor Shqip API",
        version=VERSION,
        docs=f"{origin}/docs",
        openapi=f"{origin}/openapi.json",
        no_api_key=True,
        rate_limit=f"{INBOUND_RATE_LIMIT} requests / {int(INBOUND_RATE_WINDOW)}s per IP",
        endpoints={
            "lookup": "GET /api/v1/lookup?q={word}",
            "suggest": "GET /api/v1/suggest?q={prefix}",
            "word_of_the_day": "GET /api/v1/word-of-the-day",
            "quotes": "GET /api/v1/quotes?q={word}",
            "trending": "GET /api/v1/trending",
            "sources": "GET /api/v1/sources",
            "health": "GET /api/v1/health",
        },
        example=f"{origin}/api/v1/lookup?q=dashuri",
    )


@app.get("/api/v1/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=VERSION,
        sources={item.id: item.homepage for item in SOURCES},
    )


@app.get("/api/v1/sources", response_model=list[SourceInfo], tags=["meta"])
async def list_sources() -> list[SourceInfo]:
    return SOURCES


@app.get("/api/v1/lookup", response_model=LookupResponse, tags=["dictionary"])
async def lookup_query(
    q: str = Query(..., min_length=1, max_length=80),
    source: list[SourceId] | None = Query(default=None),
) -> LookupResponse:
    return await _lookup(q, source)


@app.get("/api/v1/lookup/{word}", response_model=LookupResponse, tags=["dictionary"])
async def lookup_path(
    word: str,
    source: list[SourceId] | None = Query(default=None),
) -> LookupResponse:
    return await _lookup(word, source)


@app.get("/api/v1/suggest", response_model=SuggestResponse, tags=["dictionary"])
async def suggest(
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(8, ge=1, le=20),
) -> SuggestResponse:
    cleaned = _require_word(q)
    return await suggest_words(cleaned, limit=limit)


@app.get("/api/v1/word-of-the-day", response_model=WordOfTheDayResponse, tags=["dictionary"])
async def word_of_the_day() -> WordOfTheDayResponse:
    try:
        payload = await fjalorthi.word_of_the_day()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Word of the day is unavailable ({exc.__class__.__name__})") from exc
    if not payload:
        raise HTTPException(status_code=502, detail="Word of the day is unavailable")
    word = payload["word"]
    lookup_data = await lookup_word(word, ("fjalorthi",))
    return WordOfTheDayResponse(
        word=word,
        definition=payload.get("definition"),
        source="fjalorthi",
        url=f"https://fjalorthi.com/{word}",
        lookup=lookup_data,
    )


@app.get("/api/v1/quotes", response_model=QuotesResponse, tags=["dictionary"])
async def quotes_query(q: str = Query(..., min_length=1, max_length=80)) -> QuotesResponse:
    return await _quotes(q)


@app.get("/api/v1/quotes/{word}", response_model=QuotesResponse, tags=["dictionary"])
async def quotes_path(word: str) -> QuotesResponse:
    return await _quotes(word)


@app.get("/api/v1/trending", response_model=TrendingResponse, tags=["dictionary"])
async def trending(limit: int = Query(12, ge=1, le=40)) -> TrendingResponse:
    try:
        words = await fjalorthi.trending(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Trending words are unavailable ({exc.__class__.__name__})") from exc
    return TrendingResponse(words=words)


async def _lookup(word: str, source: list[SourceId] | None) -> LookupResponse:
    cleaned = _require_word(word)
    wanted = tuple(source) if source else ALL_SOURCES
    unknown = [item for item in wanted if item not in ALL_SOURCES]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown source: {', '.join(unknown)}")
    return await lookup_word(cleaned, wanted)


async def _quotes(word: str) -> QuotesResponse:
    cleaned = _require_word(word)
    try:
        items = await fjalorthi.quotes(cleaned)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Quotes are unavailable ({exc.__class__.__name__})") from exc
    return QuotesResponse(query=cleaned, quotes=items)


def _require_word(raw: str) -> str:
    cleaned = normalize_word(raw)
    if not is_valid_word(cleaned):
        raise HTTPException(
            status_code=400,
            detail="Use a single Albanian word (letters, hyphen, or apostrophe).",
        )
    return cleaned


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
