"""German and English for the web interface.

Built on the author's existing TranslationSystem (see translator.py), which
already defines the format this project needs: locales/translations.json with
{key: {"de": ..., "en": ...}} and a t() lookup that falls back to the key.

Two things are handled here rather than there:

* One instance per language, created once. The upstream class carries the
  current language as instance state, and flipping that per request would let
  two concurrent visitors read each other's language.
* Language resolution from the request: explicit choice first, then the
  browser's preference, then German.
"""

from pathlib import Path

from hungrycall.translator import TranslationSystem

SUPPORTED = ("de", "en")
DEFAULT_LANG = "de"
LANG_COOKIE = "hc_lang"

_PACKAGE_DIR = Path(__file__).parent

def _read_only(system: TranslationSystem) -> TranslationSystem:
    """Take the pen away from the translation system.

    Upstream, t() registers an unknown German-looking key and writes the whole
    table back to disk. That is useful in a desktop editor and destructive
    here: when the JSON failed to parse once, every lookup missed, the file was
    rewritten from the empty in-memory table, and the entire translation was
    gone in a single page load. A web app reads its locale file; it never
    writes it.
    """
    system._save_translations = lambda: None
    return system


# One system per language; both read the same locales/translations.json.
_SYSTEMS: dict[str, TranslationSystem] = {}
for _code in SUPPORTED:
    _system = _read_only(TranslationSystem(_code, app_dir=_PACKAGE_DIR))
    _system.set_language(_code)
    _SYSTEMS[_code] = _system

if not _SYSTEMS[DEFAULT_LANG].translations:
    # Empty means the file is missing or unparseable. Fail here rather than
    # serve pages full of raw key names.
    raise RuntimeError(
        f"No translations loaded from {_PACKAGE_DIR / 'locales' / 'translations.json'}. "
        "Check that the file exists and is valid JSON."
    )


def normalize_lang(value: str | None) -> str | None:
    """Reduce 'en-GB', 'EN', 'en_US' to 'en'. Unknown languages return None."""
    if not value:
        return None
    code = value.strip().lower().split(";")[0].split("_")[0].split("-")[0]
    return code if code in SUPPORTED else None


def resolve_lang(
    query_lang: str | None = None,
    cookie_lang: str | None = None,
    accept_language: str | None = None,
) -> str:
    """Pick the language for one request.

    An explicit choice always wins, and it is remembered in a cookie so the
    next page does not silently switch back.
    """
    for candidate in (query_lang, cookie_lang):
        resolved = normalize_lang(candidate)
        if resolved:
            return resolved

    for part in (accept_language or "").split(","):
        resolved = normalize_lang(part)
        if resolved:
            return resolved

    return DEFAULT_LANG


def t(key: str, lang: str = DEFAULT_LANG, **fields: object) -> str:
    """Translate a key, optionally filling {placeholders}.

    A missing key comes back as the key itself. That is deliberate: an
    untranslated string should be visible in the interface, not silently
    plausible. tests/test_i18n.py fails the build if any key is missing.
    """
    system = _SYSTEMS.get(normalize_lang(lang) or DEFAULT_LANG, _SYSTEMS[DEFAULT_LANG])
    text = system.t(key)
    if fields:
        for name, value in fields.items():
            text = text.replace("{" + name + "}", str(value))
    return text


def all_keys() -> list[str]:
    return sorted(_SYSTEMS[DEFAULT_LANG].translations.keys())


def has_key(key: str) -> bool:
    """Whether ``key`` is a real, defined translation key.

    For a caller that builds a key by interpolating a value it does not
    control (e.g. ``f"table.seating.{value}"`` where ``value`` came from
    somewhere else entirely) -- so it can show that value as plain text
    instead of the raw, unresolved key t() falls back to when the
    interpolated key does not exist.
    """
    return key in _SYSTEMS[DEFAULT_LANG].translations


def missing_translations() -> dict[str, list[str]]:
    """Keys with an empty or absent value, per language. Empty dict means done."""
    gaps: dict[str, list[str]] = {}
    table = _SYSTEMS[DEFAULT_LANG].translations
    for code in SUPPORTED:
        holes = [key for key, entry in table.items() if not entry.get(code)]
        if holes:
            gaps[code] = sorted(holes)
    return gaps
