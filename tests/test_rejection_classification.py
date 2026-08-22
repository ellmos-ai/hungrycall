"""Regression coverage for E21 (Endabnahme field-trial finding, 2026-08-22).

A call where no usable conversation ever happened (busy, no answer, or a
technically completed call with no evaluable structured result) used to be
labelled the same as a restaurant that explicitly declined a criterion, and
the raw internal reason string ("Structured result is missing required
fields: pickup_available, order_chain_results") leaked straight into the
cockpit. classify_rejection() (engine.py) tells the two apart for display;
cascade_stream_label_and_reason() (web.py) turns that into the localized
label and a human-readable reason -- both display-only, never fed back into
evaluate_result()'s pass/fail decision.
"""

import pytest

from hungrycall.engine import classify_rejection
from hungrycall.models import CallStatus
from hungrycall.web import cascade_stream_label_and_reason


def _result(status: CallStatus, **overrides):
    from hungrycall.models import CallResult

    base = {
        "call_id": "call_1",
        "run_id": "run_1",
        "status": status,
        "task_completed": False,
        "completion_confidence": 0.0,
        "structured_result": {},
        "transcript": [],
        "post_summary": "",
    }
    base.update(overrides)
    return CallResult(**base)


@pytest.mark.parametrize(
    "status",
    [
        CallStatus.FAILED,
        CallStatus.NO_ANSWER,
        CallStatus.CANCELED,
        CallStatus.VOICEMAIL,
        CallStatus.BUSY,
        CallStatus.EXPIRED,
    ],
)
def test_a_call_that_never_technically_completed_is_not_reached(status):
    result = _result(status)
    assert classify_rejection(result, f"Call failed with status '{status.value}'") == "not_reached"


def test_a_completed_call_with_no_usable_structured_result_is_not_reached():
    """Zum Falken (E21): the call completed, but nothing was actually
    discussed -- the app could not extract any usable evidence."""
    result = _result(CallStatus.COMPLETED)
    reason = "Structured result is missing required fields: pickup_available, order_chain_results"
    assert classify_rejection(result, reason) == "not_reached"


def test_a_completed_call_with_a_real_criterion_failure_is_declined():
    result = _result(CallStatus.COMPLETED)
    assert classify_rejection(result, "Doorstep total 33.00 EUR exceeds maximum budget limit of 25.00 EUR") == "declined"
    assert classify_rejection(result, "Restaurant does not deliver to specified address") == "declined"


def test_cockpit_label_and_reason_for_not_reached_hides_the_raw_field_names():
    result = _result(CallStatus.COMPLETED)
    reason = "Structured result is missing required fields: pickup_available, order_chain_results"

    label_de, reason_de = cascade_stream_label_and_reason(result, reason, "de")
    assert label_de == "Nicht erreicht"
    assert "pickup_available" not in reason_de
    assert "order_chain_results" not in reason_de

    label_en, reason_en = cascade_stream_label_and_reason(result, reason, "en")
    assert label_en == "Not reached"
    assert "pickup_available" not in reason_en


def test_cockpit_label_and_reason_for_a_real_decline_keeps_the_reason():
    result = _result(CallStatus.COMPLETED)
    reason = "Doorstep total 33.00 EUR exceeds maximum budget limit of 25.00 EUR"

    label, display_reason = cascade_stream_label_and_reason(result, reason, "en")
    assert label == "Declined"
    assert display_reason == reason


def test_no_answer_status_gets_the_not_reached_label_even_without_a_reason():
    result = _result(CallStatus.NO_ANSWER)
    label, _ = cascade_stream_label_and_reason(
        result, "Call failed with status 'NO_ANSWER'", "de"
    )
    assert label == "Nicht erreicht"
