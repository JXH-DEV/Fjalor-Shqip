from pathlib import Path

from app.htmlutil import fjalorthi_to_text, split_numbered_senses
from app.http import word_url
from app.normalize import is_valid_word, lookup_variants, normalize_word
from app.pos import canonical_pos
from app.sources.fjale import parse_entry as parse_fjale
from app.sources.fjalorth import parse_entry as parse_fjalorth
from app.sources.fjalorthi import parse_define
from app.sources.wiktionary import parse_en_definitions, parse_sq_html

FIXTURES = Path(__file__).parent / "fixtures"


def test_normalize_word_keeps_albanian_letters():
    assert normalize_word("  Shtëpi\n") == "Shtëpi"
    assert is_valid_word("shtëpi")
    assert is_valid_word("t'ia")
    assert not is_valid_word("../etc/passwd")
    assert not is_valid_word("")


def test_lookup_variants_fold_schwa():
    variants = lookup_variants("shtëpi")
    assert "shtëpi" in variants
    assert "shtepi" in variants


def test_word_url_percent_encodes_albanian():
    url = word_url("https://fjale.al", "shtëpi")
    assert "%C3%AB" in url


def test_canonical_pos():
    assert canonical_pos(["f.", "emër i gjinisë femërore", "Noun"]) == ["noun"]
    assert "verb" in canonical_pos(["folje kalimtare"])


def test_fjale_parser_accepts_b_and_ul():
    html = (FIXTURES / "fjale_shtepi.html").read_text(encoding="utf-8")
    entries = parse_fjale(html)
    assert entries[0].headword == "SHTËPI"
    assert entries[0].part_of_speech == ["f"]
    assert entries[0].senses[0].gloss.startswith("Ndërtesë")
    assert len(entries[0].senses) == 2


def test_fjale_parser_extracts_senses_and_related():
    html = (FIXTURES / "fjale_dashuri.html").read_text(encoding="utf-8")
    entries = parse_fjale(html)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.headword == "DASHURI"
    assert entry.part_of_speech == ["f."]
    assert len(entry.senses) == 3
    assert entry.senses[0].examples == ["Dashuri prindërore."]
    assert "keq" in " ".join(entry.senses[2].labels).casefold() or entry.senses[2].labels
    assert "dashur" in entry.related
    assert "dashuroj" in entry.related


def test_fjalorth_parser_reads_translation():
    html = (FIXTURES / "fjalorth_dashuri.html").read_text(encoding="utf-8")
    entries = parse_fjalorth(html)
    assert entries[0].headword == "DASHURI"
    assert entries[0].translations["en"] == ["LOVE"]
    assert len(entries[0].senses) == 2


def test_fjalorthi_define_parser():
    payload = {
        "searchedWord": "dashuri",
        "exactMatches": [
            {
                "word": "dashuri",
                "word5": "dashurí",
                "wordDefinition": (
                    'dashurí,-a <span class="SHRT" data-short="f">emër i gjinisë femërore;</span> '
                    "1. ndjenjë e fuqishme. 2. prirje e brendshme."
                ),
                "wordDer1": "dashuria",
                "exactMatch": True,
                "canonicalWord": "dashuri",
                "synonyms": ["lakmi"],
                "antonyms": [],
            }
        ],
        "fuzzyMatches": [],
    }
    entries = parse_define(payload)
    assert entries[0].headword == "dashuri"
    assert any("emër" in pos for pos in entries[0].part_of_speech)
    assert [sense.number for sense in entries[0].senses] == [1, 2]
    assert "lakmi" in entries[0].synonyms


def test_split_numbered_senses():
    senses = split_numbered_senses("lemma (emër) 1. first gloss. 2. second gloss.")
    assert senses[0] == (1, "first gloss.")
    assert senses[1][0] == 2


def test_fjalorthi_html_labels():
    text, labels = fjalorthi_to_text(
        'fjalë <span class="SHRT" data-short="f">emër i gjinisë femërore;</span> kuptim'
    )
    assert "emër i gjinisë femërore" in labels[0]
    assert "<span" not in text


def test_wiktionary_en_parser():
    payload = {
        "sq": [
            {
                "partOfSpeech": "Noun",
                "definitions": [
                    {"definition": '<a href="/wiki/love">love</a>'},
                    {"definition": "affection"},
                ],
            }
        ]
    }
    entries = parse_en_definitions("dashuri", payload)
    assert entries[0].translations["en"] == ["love", "affection"]
    assert entries[0].part_of_speech == ["Noun"]


def test_wiktionary_sq_parser():
    html = """
    <div class="mw-parser-output">
      <div class="mw-heading"><h3>Emër</h3></div>
      <ol>
        <li>Ndjenjë e fuqishme</li>
        <li>Ndjenjë e zjarrtë</li>
      </ol>
    </div>
    """
    entries = parse_sq_html("dashuri", html)
    assert entries[0].part_of_speech == ["Emër"]
    assert len(entries[0].senses) == 2
