"""German and English must both be complete, and stay complete.

A half-translated interface is worse than a monolingual one: it looks finished
and is not. These tests are the guard that keeps that from shipping unnoticed.
"""

import json
import re
from pathlib import Path

import pytest

from hungrycall.i18n import (
    DEFAULT_LANG,
    SUPPORTED,
    all_keys,
    missing_translations,
    normalize_lang,
    resolve_lang,
    t,
)

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "hungrycall"
LOCALE_FILE = PACKAGE_DIR / "locales" / "translations.json"

# Matches t("some.key" ...) but not dict.get("x") or result.get("x").
KEY_CALL = re.compile(r"(?<![\w.])t\(\s*[\"']([a-z][a-z0-9_.]*)[\"']")
# Matches the two places a key is assembled: t(f"result.title.{...}") etc.
PREFIX_CALL = re.compile(r"(?<![\w.])t\(\s*f?[\"']([a-z][a-z0-9_.]*\.)\{")


def test_locale_file_is_valid_json_and_not_empty():
    """The file parsed. When it did not, the app silently erased it once."""
    data = json.loads(LOCALE_FILE.read_text(encoding="utf-8"))
    assert len(data) > 100
    assert all(set(entry) >= {"de", "en"} for entry in data.values())


def test_no_language_has_gaps():
    assert missing_translations() == {}


@pytest.mark.parametrize("lang", SUPPORTED)
def test_every_key_used_in_code_exists(lang):
    """Every literal key the code asks for is defined.

    Missing keys do not crash — t() returns the key — so nothing would fail at
    runtime except that the page reads 'landing.claim' to a human.
    """
    defined = set(all_keys())
    referenced = set()
    prefixes = set()

    for path in PACKAGE_DIR.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for hit in KEY_CALL.findall(source):
            # t("table.concession." + key): a trailing dot means the key is
            # assembled, so it is a family, not a literal.
            (prefixes if hit.endswith(".") else referenced).add(hit)
        prefixes |= set(PREFIX_CALL.findall(source))

    assert referenced, "no translation keys found at all — has the regex drifted?"
    assert not (referenced - defined), f"undefined keys: {sorted(referenced - defined)}"

    # Dynamically built keys must have at least one definition per prefix,
    # otherwise a whole family (result.title.*) can silently go missing.
    for prefix in prefixes:
        assert any(key.startswith(prefix) for key in defined), f"no keys for prefix {prefix}"


def test_dynamic_key_families_are_complete():
    """The families the code builds at runtime, spelled out."""
    from hungrycall.models import Mode, Seating
    from hungrycall.templates import FOOD_CONCESSIONS

    defined = set(all_keys())
    for mode in Mode:
        assert f"result.title.{mode.value}" in defined
    for seating in Seating:
        assert f"table.seating.{seating.value}" in defined
    for concession in FOOD_CONCESSIONS:
        assert f"food.concession.{concession.key}" in defined


def test_translations_actually_differ_between_languages():
    """Guards against an 'English' column that is just the German copied over."""
    data = json.loads(LOCALE_FILE.read_text(encoding="utf-8"))
    identical = [k for k, v in data.items() if v["de"] == v["en"]]
    # A handful legitimately match (product name, 'I am hungry').
    assert len(identical) <= 3, f"suspiciously many identical entries: {identical}"


def test_placeholders_survive_translation():
    """A {name} lost in translation produces a sentence with a hole in it."""
    data = json.loads(LOCALE_FILE.read_text(encoding="utf-8"))
    for key, entry in data.items():
        de_slots = set(re.findall(r"\{(\w+)\}", entry["de"]))
        en_slots = set(re.findall(r"\{(\w+)\}", entry["en"]))
        assert de_slots == en_slots, f"{key}: {de_slots} vs {en_slots}"


def test_t_fills_placeholders():
    assert "Trattoria" in t("cascade.dialing", "de", name="Trattoria")
    assert "Trattoria" in t("cascade.dialing", "en", name="Trattoria")


def test_unknown_key_comes_back_visible_and_changes_nothing_on_disk():
    """A missing key must be loud, and must not rewrite the locale file."""
    before = LOCALE_FILE.read_bytes()
    assert t("no.such.key.exists", "de") == "no.such.key.exists"
    assert LOCALE_FILE.read_bytes() == before


def test_language_resolution_order():
    assert resolve_lang(query_lang="en", cookie_lang="de") == "en"
    assert resolve_lang(cookie_lang="en") == "en"
    assert resolve_lang(accept_language="en-GB,en;q=0.9") == "en"
    assert resolve_lang() == DEFAULT_LANG
    assert resolve_lang(query_lang="fr", accept_language="fr-FR") == DEFAULT_LANG
    assert normalize_lang("EN_us") == "en"
    assert normalize_lang("klingon") is None
