"""Regression coverage for human callbacks and bounded table fallbacks."""

import json
import sqlite3

from hungrycall.db import (
    create_order_record,
    init_db,
    list_order_records,
    list_saved_results,
    save_cascade_result,
)
from hungrycall.engine import CascadeEngine, build_call_goal
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.models import CallResult, CallStatus, Mode, Seating, UserRequest
from hungrycall.schemas import get_result_schema
from hungrycall.safety import SafetyError
from hungrycall.web import build_user_request
from hungrycall.templates import render_history


CALLBACK = "+4910004069000"


def reservation_request(**overrides):
    values = {
        "mode": Mode.RESERVATION,
        "customer_name": "Ada Lovelace",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "requester_callback_number": CALLBACK,
        "food_prompt": "Italian",
        "reservation_date": "2026-08-07",
        "reservation_time": "19:00",
        "party_size": 4,
    }
    values.update(overrides)
    return UserRequest(**values)


def reservation_result(**structured):
    base = {
        "table_available": True,
        "reservation_confirmed": True,
        "reservation_date_confirmed": "2026-08-07",
        "reservation_time_confirmed": "19:00",
        "seating_preference_met": True,
        "booking_fee_eur": 0,
        "authority_steps_applied": [],
    }
    base.update(structured)
    return CallResult(
        call_id="dry-call",
        run_id="dry-run",
        status=CallStatus.COMPLETED,
        task_completed=True,
        completion_confidence=1.0,
        structured_result=base,
        transcript=[],
        post_summary="",
    )


def test_web_request_requires_and_normalizes_the_human_callback():
    base = {
        "mode": "delivery",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "requester_callback_number": "+49 100 04069000",
        "food_prompt": "one pizza",
        "max_budget_eur": "25",
        "delivery_address": "Example Street 1",
    }
    request = build_user_request(base, day_override="Fri", time_override="19:00")

    assert request.customer_name == "Ada Lovelace"
    assert request.requester_callback_number == CALLBACK

    without_callback = dict(base)
    without_callback.pop("requester_callback_number")
    try:
        build_user_request(without_callback, day_override="Fri", time_override="19:00")
    except ValueError as exc:
        assert "requester_callback_number" in str(exc)
    else:
        raise AssertionError("a request without the mandatory callback number was accepted")


def test_every_goal_ends_with_the_human_confirmation_handoff():
    for mode in (Mode.DELIVERY, Mode.PICKUP, Mode.RESERVATION):
        request = reservation_request(mode=mode)
        request.max_budget_eur = 30
        request.delivery_address = "Example Street 1"
        request.pickup_time = "19:30"
        goal = build_call_goal(SAMPLE_RESTAURANTS[0], request)

        assert "Ada Lovelace" in goal
        assert CALLBACK in goal
        assert "with questions" in goal
        assert "human confirmation" in goal
        assert goal.rfind(CALLBACK) > goal.find("automated assistant")
        assert goal.endswith("repeat it once at the end.")


def test_reservation_goal_grants_time_and_fee_only_in_stages():
    request = reservation_request(
        seating=Seating.CUSTOM,
        seating_custom="our usual table under the palm tree",
        special_instructions="Please note the birthday cake.",
        earlier_hours=1,
        earlier_minutes=30,
        later_hours=2,
        later_minutes=15,
        max_booking_fee_eur=3,
    )
    goal = build_call_goal(SAMPLE_RESTAURANTS[1], request)

    assert "up to 90 minutes earlier" in goal
    assert "up to 135 minutes later" in goal
    assert "up to 3.00 EUR" in goal
    assert goal.index("exact stated time") < goal.index("minutes earlier")
    assert goal.index("minutes earlier") < goal.index("minutes later")
    assert goal.index("minutes later") < goal.index("up to 3.00 EUR")
    assert "usual table under the palm tree" in goal
    assert "birthday cake" in goal


def test_reservation_result_must_stay_within_time_and_fee_authority():
    engine = CascadeEngine(SAMPLE_RESTAURANTS)
    request = reservation_request(
        earlier_hours=1,
        later_minutes=30,
        max_booking_fee_eur=3,
    )

    accepted, reason = engine.evaluate_result(
        request,
        reservation_result(
            reservation_time_confirmed="18:00",
            booking_fee_eur=3,
            authority_steps_applied=["earlier_time", "booking_fee"],
        ),
    )
    assert accepted is True and reason is None

    accepted, reason = engine.evaluate_result(
        request,
        reservation_result(
            reservation_time_confirmed="17:59",
            authority_steps_applied=["earlier_time"],
        ),
    )
    assert accepted is False and "only 60 minutes" in reason

    accepted, reason = engine.evaluate_result(
        request,
        reservation_result(
            reservation_time_confirmed="19:31",
            authority_steps_applied=["later_time"],
        ),
    )
    assert accepted is False and "only 30 minutes" in reason

    accepted, reason = engine.evaluate_result(
        request,
        reservation_result(booking_fee_eur=3.01, authority_steps_applied=["booking_fee"]),
    )
    assert accepted is False and "exceeds the authorised maximum" in reason


def test_used_reservation_fallback_requires_an_auditable_authority_report():
    engine = CascadeEngine(SAMPLE_RESTAURANTS)
    request = reservation_request(later_hours=1)
    accepted, reason = engine.evaluate_result(
        request,
        reservation_result(reservation_time_confirmed="19:30"),
    )

    assert accepted is False
    assert "without an auditable authority report" in reason


def test_unconfirmed_custom_table_preference_is_not_silently_accepted():
    engine = CascadeEngine(SAMPLE_RESTAURANTS)
    request = reservation_request(
        seating=Seating.CUSTOM,
        seating_custom="our usual table under the palm tree",
    )

    accepted, reason = engine.evaluate_result(
        request,
        reservation_result(seating_preference_met=False),
    )
    assert accepted is False
    assert "custom seating preference" in reason


def test_custom_seating_requires_text_and_positive_confirmation():
    base = {
        "mode": "reservation",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "requester_callback_number": CALLBACK,
        "food_prompt": "Italian",
        "reservation_date": "2026-08-07",
        "reservation_time": "19:00",
        "party_size": "4",
        "seating": "custom",
    }
    try:
        build_user_request(base)
    except ValueError as exc:
        assert "seating_custom is required" in str(exc)
    else:
        raise AssertionError("empty custom seating was accepted")

    inconsistent = dict(base, seating="any", seating_custom="under the palm")
    try:
        build_user_request(inconsistent)
    except ValueError as exc:
        assert "requires custom seating" in str(exc)
    else:
        raise AssertionError("custom text without custom mode was accepted")

    engine = CascadeEngine(SAMPLE_RESTAURANTS)
    request = reservation_request(seating=Seating.CUSTOM, seating_custom="under the palm")
    missing_confirmation = reservation_result()
    missing_confirmation.structured_result.pop("seating_preference_met", None)
    accepted, reason = engine.evaluate_result(request, missing_confirmation)
    assert accepted is False
    assert "missing required fields" in reason


def test_legacy_reservation_concessions_cannot_expand_new_limits():
    fields = {
        "mode": "reservation",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "requester_callback_number": CALLBACK,
        "food_prompt": "Italian",
        "reservation_date": "2026-08-07",
        "reservation_time": "19:00",
        "party_size": "4",
        "seating": "any",
        "max_booking_fee_eur": "3",
        "concessions": ["time_flex", "deposit_ok"],
    }
    request = build_user_request(fields)
    assert request.concessions == []
    goal = build_call_goal(SAMPLE_RESTAURANTS[0], request)
    assert "up to 3.00 EUR" in goal
    assert "15 EUR" not in goal
    assert "one hour earlier" not in goal


def test_free_reservation_notes_share_the_high_risk_content_gate():
    request = reservation_request(special_instructions="Please call the hospital instead")
    engine = CascadeEngine(SAMPLE_RESTAURANTS)
    try:
        engine.run(request)
    except SafetyError as exc:
        assert "prohibited term 'hospital'" in str(exc)
    else:
        raise AssertionError("high-risk content in the note bypassed the safety gate")


def test_live_reservation_schema_requires_authority_evidence():
    schema = get_result_schema(Mode.RESERVATION)
    required = set(schema["required"])

    assert {
        "reservation_date_confirmed",
        "reservation_time_confirmed",
        "booking_fee_eur",
        "authority_steps_applied",
    } <= required


def test_requester_callback_is_transient_and_never_persisted(tmp_path, monkeypatch):
    database = tmp_path / "callback-privacy.db"
    monkeypatch.setenv("HUNGRYCALL_DB_PATH", str(database))
    init_db(str(database))
    request = build_user_request(
        {
            "mode": "delivery",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "requester_callback_number": CALLBACK,
            "food_prompt": "one pizza",
            "max_budget_eur": "25",
            "delivery_address": "Example Street 1",
        },
        day_override="Fri",
        time_override="19:00",
    )
    create_order_record(
        order_id="privacy-order",
        mode=request.mode.value,
        customer_name=request.customer_name,
        food_prompt=request.food_prompt,
        max_budget_eur=request.max_budget_eur,
        delivery_address=request.delivery_address,
    )
    leaky_result = CallResult(
        call_id="leaky-call",
        run_id="leaky-run",
        status=CallStatus.COMPLETED,
        task_completed=True,
        completion_confidence=1.0,
        structured_result={
            "order_placed": True,
            "requester_callback_number": CALLBACK,
            "debug": {
                "echo": f"Call {CALLBACK} for confirmation",
                "local_echo": "Call 0100 04069000 for confirmation",
            },
            "rejection_reason": f"Restaurant repeated {CALLBACK}",
        },
        transcript=[{"text": f"Human number: {CALLBACK}"}],
        post_summary=f"Confirmation via {CALLBACK}",
        rejection_reason=f"Echoed {CALLBACK}",
        activity=[f"Callee repeated {CALLBACK}"],
        raw_transcript_text=f"Number {CALLBACK}",
    )
    CascadeEngine.redact_requester_callback(leaky_result, CALLBACK)
    assert CALLBACK not in json.dumps(
        {
            "structured": leaky_result.structured_result,
            "transcript": leaky_result.transcript,
            "summary": leaky_result.post_summary,
            "reason": leaky_result.rejection_reason,
            "activity": leaky_result.activity,
            "raw": leaky_result.raw_transcript_text,
        }
    )
    assert "0100 04069000" not in json.dumps(leaky_result.structured_result)
    assert "requester_callback_number" not in leaky_result.structured_result

    save_cascade_result(
        result_id="privacy-result",
        order_id="privacy-order",
        mode=request.mode.value,
        restaurant_id="restaurant-1",
        restaurant_name="Example Restaurant",
        masked_phone="+491 ••• ••••222",
        callback_number="+441632960001",
        total_price_eur=20,
        eta_minutes=30,
        post_summary=leaky_result.post_summary,
        raw_transcript_text=leaky_result.raw_transcript_text,
        structured_result=leaky_result.structured_result,
    )

    with sqlite3.connect(database) as connection:
        order_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(orders)")
        }
        result_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(saved_results)")
        }
    assert "requester_callback_number" not in order_columns
    assert "requester_callback_number" not in result_columns

    orders = list_order_records()
    saved = list_saved_results()
    serialized = json.dumps({"orders": orders, "saved_results": saved})
    assert CALLBACK not in serialized
    assert all("requester_callback_number" not in row for row in orders + saved)
    assert CALLBACK not in render_history("en", saved, orders)
    assert CALLBACK.encode("utf-8") not in database.read_bytes()


def test_callback_spoken_as_digit_words_across_turns_is_still_redacted():
    """Reproduces the 2026-08-11 field-trial leak end to end, through the
    actual code path (CascadeEngine.redact_requester_callback ->
    phone_utils.redact_specific_phone): the voice agent read the requester's
    callback number aloud as German digit words, and CALL-E's transcript
    reconstruction split it across two turn-header lines. The digits below
    spell CALLBACK ("+4910004069000") -> vier neun eins null null eins
    zwei drei vier fünf sechs sieben acht."""
    raw_transcript = (
        "[01:10] BOT: Die direkte Rückrufnummer ist plus vier neun,\n"
        "[01:15] BOT: eins null null, eins zwei drei, vier fünf sechs, sieben acht."
    )
    leaky_result = CallResult(
        call_id="spelled-out-call",
        run_id="spelled-out-run",
        status=CallStatus.COMPLETED,
        task_completed=True,
        completion_confidence=1.0,
        structured_result={"order_placed": True},
        transcript=[],
        post_summary="Reservierung bestätigt.",
        rejection_reason=None,
        activity=[],
        raw_transcript_text=raw_transcript,
    )
    CascadeEngine.redact_requester_callback(leaky_result, CALLBACK)
    assert "[REDACTED-REQUESTER-CALLBACK]" in leaky_result.raw_transcript_text
    assert "vier" not in leaky_result.raw_transcript_text
    assert "sieben" not in leaky_result.raw_transcript_text
    # The rest of the transcript, including the turn headers, is untouched.
    assert "[01:10] BOT:" in leaky_result.raw_transcript_text
    assert "Die direkte Rückrufnummer ist" in leaky_result.raw_transcript_text
