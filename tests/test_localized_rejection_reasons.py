"""Regression coverage for E19 (Endabnahme field-trial finding, 2026-08-22).

engine.evaluate_result() (and its private check_* helpers) build the pass/
fail judgment as a hardcoded English string, because that value is stored to
call_attempts, returned by the API and printed by the CLI -- all of which
stay English on purpose. The live cockpit is the one place a person running
a German session actually reads that judgment, and it showed the raw English
text unchanged: reason "Order was not placed" (Asia Imbiss) appeared
verbatim in the German cockpit. localize_engine_reason() (web.py) maps the
code's own hardcoded fallback reasons to a translation key for display only;
the underlying (passed, rejection_reason) value from evaluate_result() is
unchanged, exactly like the E21 fix this one sits next to.
"""

import pytest

from hungrycall.models import CallResult, CallStatus
from hungrycall.web import cascade_stream_label_and_reason, localize_engine_reason


def _completed_result() -> CallResult:
    return CallResult(
        call_id="call_1",
        run_id="run_1",
        status=CallStatus.COMPLETED,
        task_completed=False,
        completion_confidence=0.0,
        structured_result={},
        transcript=[],
        post_summary="",
    )


@pytest.mark.parametrize(
    ("english_reason", "german_text"),
    [
        ("Order was not placed", "Bestellung wurde nicht aufgegeben"),
        (
            "Restaurant does not deliver to specified address",
            "Restaurant liefert nicht an die angegebene Adresse",
        ),
        ("Pickup not available at restaurant", "Abholung wird von diesem Restaurant nicht angeboten"),
        (
            "No table available for requested date and time",
            "Kein Tisch für den gewünschten Termin verfügbar",
        ),
        ("Reservation was not confirmed", "Reservierung wurde nicht bestätigt"),
        (
            "The custom seating preference was not confirmed",
            "Der gewünschte Sitzplatzwunsch wurde nicht bestätigt",
        ),
        (
            "Unclear price statement (vague or missing exact quote)",
            "Unklare Preisangabe (vage oder ohne genauen Betrag)",
        ),
        ("Unclear price statement: total_price_eur missing", "Unklare Preisangabe: Gesamtpreis fehlt"),
        ("Order wish chain did not resolve", "Bestellwunschkette konnte nicht aufgelöst werden"),
    ],
)
def test_engine_s_own_hardcoded_reasons_are_translated_to_german(english_reason, german_text):
    """Asia Imbiss (E19): the app's own fallback judgment text, not the
    call's, must read in German during a German session."""
    assert localize_engine_reason(english_reason, "de") == german_text
    # And stays the same English text in an English session -- this is a
    # translation, not a rewrite of the canonical value.
    assert localize_engine_reason(english_reason, "en") == english_reason


def test_cockpit_shows_the_localized_reason_for_a_real_decline():
    result = _completed_result()

    label_de, reason_de = cascade_stream_label_and_reason(result, "Order was not placed", "de")
    assert label_de == "Abgelehnt"
    assert reason_de == "Bestellung wurde nicht aufgegeben"
    assert "Order was not placed" not in reason_de


def test_a_reason_the_call_itself_supplied_is_left_exactly_as_received():
    """Text struct.get("rejection_reason") pulled straight from the call's
    own structured result was authored by the call, not by this code, and is
    not this fix's to translate -- unlike engine.py's own hardcoded
    fallbacks, it passes through unchanged in both languages."""
    result = _completed_result()
    reason = "The kitchen closes in ten minutes, they cannot take this order"

    _, reason_de = cascade_stream_label_and_reason(result, reason, "de")
    _, reason_en = cascade_stream_label_and_reason(result, reason, "en")

    assert reason_de == reason
    assert reason_en == reason


def test_a_dynamic_engine_message_is_left_untranslated_for_now():
    """Interpolated messages (a budget figure, a seating mismatch) are not in
    the static table on purpose -- see the comment above
    _STATIC_ENGINE_REASON_KEYS in web.py -- and must not be silently dropped
    or garbled while unhandled."""
    reason = "Doorstep total 33.00 EUR exceeds maximum budget limit of 25.00 EUR"
    assert localize_engine_reason(reason, "de") == reason
