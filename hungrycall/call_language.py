"""Single seam for the language a live call is conducted in.

Two independent things read this seam: the transport (``call_client.py``)
sets ``region``/``locale`` on the CALL-E recipient, and the goal builder
(``engine.py``/``order_chains.py``) picks which language its VERBATIM-quoted
sentences ship in. German stays the default so unset-environment behaviour is
byte-identical to before this module existed (field trial 2026-08-11 proved
that a quoted sentence is spoken exactly as written, in whichever language it
was written — see AGENTS.md and FINDINGS.md).

Only literally quoted fragments need a translation. Everything else in a
goal is a meta-instruction that CALL-E rephrases into the call's own
language on its own; that split is why ``build_call_goal`` and
``build_order_chain_instruction`` translate only their quoted examples and
leave the rest of the English instruction text untouched regardless of the
resolved locale.

Deliberately the ONLY lever: there is no separate ``--language`` CLI flag or
web-form field, and none should be added that bypasses ``call_language()`` --
a sister project shipped one that did (2026-08-11, reported by the operator):
its own language flag never propagated to the CALL-E recipient's region/locale,
so the two drifted apart (a plan reported "de (en-US, region US)"). Here the
recipient's region/locale (``call_client.py``) and the goal text's language
(``engine.py``/``order_chains.py``) both come from calling this same function,
so they cannot drift apart the way that did — see
``tests/test_call_client.py::test_recipient_region_locale_and_goal_language_cannot_diverge``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

CALL_LOCALE_ENV = "HUNGRYCALL_CALL_LOCALE"
DEFAULT_CALL_LOCALE = "de"
SUPPORTED_CALL_LOCALES = ("de", "en")


@dataclass(frozen=True)
class CallLanguage:
    """The resolved language for one live call."""

    locale: str  # CALL-E recipient locale, e.g. "de" or "en"
    region: str  # CALL-E recipient region, e.g. "DE"


# CALL-E documents Germany as the supported region and English/German as the
# supported spoken languages (AGENTS.md: "Deutschland wird unterstützt,
# Sprachen Englisch und Deutsch"). There is no confirmed non-DE region, and
# HungryCall's own candidate search (geo.py, ranking.py) targets German
# addresses. An "en" call locale therefore changes the language spoken on
# the call, not the dialled country: it still dials region "DE". This is an
# honest limitation, not a guess — it serves demo/jury runs and future
# international deployments that still call into Germany, not a claim that
# CALL-E can reach restaurants abroad.
_REGION_BY_LOCALE = {
    "de": "DE",
    "en": "DE",
}


def call_language(environment: Mapping[str, str] | None = None) -> CallLanguage:
    """Resolve the language a live call is conducted in.

    Reads ``HUNGRYCALL_CALL_LOCALE`` (case-insensitive); unset or
    unsupported values fall back to German, so the historic single-language
    behaviour is unchanged unless the operator opts in. A bad locale is not
    a safety issue the way an unverified phone number is (contrast
    ``field_trial.py``), so it degrades to the well-tested default instead
    of refusing the call.
    """
    environ = os.environ if environment is None else environment
    raw = (environ.get(CALL_LOCALE_ENV) or "").strip().lower()
    locale = raw if raw in SUPPORTED_CALL_LOCALES else DEFAULT_CALL_LOCALE
    return CallLanguage(locale=locale, region=_REGION_BY_LOCALE[locale])
