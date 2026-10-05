from fastapi.testclient import TestClient

from app.lookup import lookup_word
from app.main import app
from app.models import LookupResponse, Sense, SourceEntry, SourceResult


def test_health():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "fjale" in body["sources"]


def test_api_index():
    client = TestClient(app)
    response = client.get("/api/v1")
    assert response.status_code == 200
    body = response.json()
    assert body["no_api_key"] is True
    assert "lookup" in body["endpoints"]


def test_lookup_query_string(monkeypatch):
    async def fake_lookup(word, sources=None):
        return LookupResponse(
            query=word,
            canonical=word,
            found=True,
            merged=None,
            sources=[],
        )

    monkeypatch.setattr("app.main.lookup_word", fake_lookup)
    client = TestClient(app)
    response = client.get("/api/v1/lookup", params={"q": "shtëpi"})
    assert response.status_code == 200
    assert response.json()["query"] == "shtëpi"
    assert "X-RateLimit-Limit" in response.headers


def test_sources_catalog():
    client = TestClient(app)
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert ids == {"fjale", "fjalorthi", "fjalorth", "wiktionary_en", "wiktionary_sq"}


def test_lookup_rejects_junk():
    client = TestClient(app)
    response = client.get("/api/v1/lookup/not_a_word!")
    assert response.status_code == 400


def test_explorer_renders():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Fjalor Shqip" in response.text
    assert "/docs" in response.text


def test_lookup_endpoint_uses_service(monkeypatch):
    async def fake_lookup(word, sources=None):
        return LookupResponse(
            query=word,
            canonical=word,
            found=True,
            merged=None,
            sources=[
                SourceResult(
                    source="fjale",
                    title="FJALË",
                    homepage="https://fjale.al/",
                    license="test",
                    found=True,
                    entries=[
                        SourceEntry(
                            headword=word,
                            senses=[Sense(number=1, gloss="kuptim prove")],
                        )
                    ],
                )
            ],
        )

    monkeypatch.setattr("app.main.lookup_word", fake_lookup)
    client = TestClient(app)
    response = client.get("/api/v1/lookup/dashuri")
    assert response.status_code == 200
    assert response.json()["found"] is True
    assert response.json()["sources"][0]["entries"][0]["senses"][0]["gloss"] == "kuptim prove"


def test_merge_prefers_long_senses(monkeypatch):
    from app.cache import cache

    cache.clear()

    async def fake_fjale(word):
        return SourceResult(
            source="fjale",
            title="FJALË",
            homepage="https://fjale.al/",
            license="t",
            found=True,
            entries=[
                SourceEntry(
                    headword="dashuri",
                    part_of_speech=["f."],
                    senses=[Sense(number=1, gloss="Ndjenjë e fuqishme, e thellë që të lidh ngushtë.")],
                    related=["dashuroj"],
                    exact_match=True,
                )
            ],
        )

    async def fake_en(word):
        return SourceResult(
            source="wiktionary_en",
            title="English Wiktionary",
            homepage="https://en.wiktionary.org/",
            license="CC BY-SA 4.0",
            found=True,
            entries=[
                SourceEntry(
                    headword="dashuri",
                    senses=[Sense(number=1, gloss="love")],
                    translations={"en": ["love"]},
                    exact_match=True,
                )
            ],
        )

    monkeypatch.setattr("app.sources.fjale.lookup", fake_fjale)
    monkeypatch.setattr("app.sources.fjalorthi.lookup", fake_en)
    monkeypatch.setattr("app.sources.fjalorth.lookup", fake_en)
    monkeypatch.setattr("app.sources.wiktionary.lookup_en", fake_en)
    monkeypatch.setattr("app.sources.wiktionary.lookup_sq", fake_en)

    import asyncio

    result = asyncio.run(lookup_word("dashuri"))
    assert result.found
    assert result.merged.senses[0].gloss.startswith("Ndjenjë")
    assert result.merged.translations["en"] == ["love"]
    assert "dashuroj" in result.merged.related
    assert "noun" in result.merged.pos
