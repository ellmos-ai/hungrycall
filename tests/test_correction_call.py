"""E41: correction-call queue by error severity.

Covers, in order: (1) classify_attempt_severity() -- the call_attempts-based
severity classification, one test per status/reason bucket; (2)
build_correction_call_goal() (via build_call_goal()'s dispatch) -- privacy by
construction (never reads food_prompt/delivery_address/max_budget_eur even
when they ARE set on the request), the self-reference-first ordering
(ringedingeding R21 precedent), and that the mandate clause explicitly rules
out a new order/reservation, in both languages; (3) the idempotency key a
correction call gets never collides with the original attempt's (R20); (4)
the manual-trigger-only web route -- refuses a clean/already-passed/already-
corrected/phone-less attempt, and on a genuine CRITICAL attempt places
exactly one new call_attempts row linked back via corrects_attempt_id.
"""

import os

import pytest
from fastapi.testclient import TestClient

from hungrycall.call_language import CALL_LOCALE_ENV
from hungrycall.db import (
    create_order_record,
    get_call_attempt,
    init_db,
    list_call_attempts,
    record_call_attempt,
)
from hungrycall.engine import build_call_goal, classify_attempt_severity
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.models import AttemptSeverity, Mode, UserRequest
from hungrycall.safety import generate_idempotency_key
from hungrycall.web import app

RESTAURANT = SAMPLE_RESTAURANTS[0]  # build_correction_call_goal never reads it


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Isolated temporary database, same pattern as test_web.py."""
    db_file = str(tmp_path / "test_hungrycall.db")
    os.environ["HUNGRYCALL_DB_PATH"] = db_file
    init_db(db_file)
    yield db_file
    os.environ.pop("HUNGRYCALL_DB_PATH", None)


@pytest.fixture
def client():
    return TestClient(app)


def _correction_request(mode: Mode, **overrides) -> UserRequest:
    fields = {
        "mode": mode,
        "customer_name": "Erika Musterfrau",
        "food_prompt": "",
        "is_correction": True,
        "corrects_attempt_id": "att_original",
    }
    fields.update(overrides)
    return UserRequest(**fields)


# --------------------------------------------------------------------------
# classify_attempt_severity()
# --------------------------------------------------------------------------

def test_a_passed_attempt_needs_no_correction():
    attempt = {"passed": 1, "status": "COMPLETED", "rejection_reason": None}
    assert classify_attempt_severity(attempt, Mode.DELIVERY) == AttemptSeverity.NONE


@pytest.mark.parametrize("mode,reason", [
    (Mode.DELIVERY, "Restaurant does not deliver to specified address"),
    (Mode.PICKUP, "Pickup not available at restaurant"),
    (Mode.RESERVATION, "No table available for requested date and time"),
])
def test_a_clean_explicit_decline_is_low_severity(mode, reason):
    attempt = {"passed": 0, "status": "COMPLETED", "rejection_reason": reason}
    assert classify_attempt_severity(attempt, mode) == AttemptSeverity.LOW


@pytest.mark.parametrize("status", ["FAILED", "NO_ANSWER", "BUSY", "CANCELED", "DECLINED"])
def test_a_call_that_never_really_connected_or_was_cleanly_closed_is_low_severity(status):
    attempt = {"passed": 0, "status": status, "rejection_reason": None}
    assert classify_attempt_severity(attempt, Mode.DELIVERY) == AttemptSeverity.LOW
    assert classify_attempt_severity(attempt, Mode.RESERVATION) == AttemptSeverity.LOW


def test_a_voicemail_message_is_moderate_severity_for_an_order():
    attempt = {"passed": 0, "status": "VOICEMAIL", "rejection_reason": None}
    assert classify_attempt_severity(attempt, Mode.DELIVERY) == AttemptSeverity.MODERATE
    assert classify_attempt_severity(attempt, Mode.PICKUP) == AttemptSeverity.MODERATE


def test_a_call_that_expired_mid_conversation_is_critical_for_an_actual_order():
    """The classic E41 field-trial case: the call was live, then just
    stopped, with no clean 'no' ever said."""
    attempt = {"passed": 0, "status": "EXPIRED", "rejection_reason": None}
    assert classify_attempt_severity(attempt, Mode.DELIVERY) == AttemptSeverity.CRITICAL
    assert classify_attempt_severity(attempt, Mode.PICKUP) == AttemptSeverity.CRITICAL
    assert classify_attempt_severity(attempt, Mode.RESERVATION) == AttemptSeverity.MODERATE


def test_a_completed_call_rejected_for_a_reason_other_than_a_clean_decline_is_ambiguous():
    """'Restaurant glaubte an eine Bestellung, App verwarf sie' -- the call
    completed, a conversation happened, but this app's OWN validation (an
    authority/budget/order-chain rule) rejected it after the fact. The
    restaurant may believe something was agreed."""
    attempt = {
        "passed": 0,
        "status": "COMPLETED",
        "rejection_reason": "Confirmed booking fee 5.00 EUR exceeds the authorised maximum of 0.00 EUR",
    }
    assert classify_attempt_severity(attempt, Mode.DELIVERY) == AttemptSeverity.CRITICAL
    assert classify_attempt_severity(attempt, Mode.PICKUP) == AttemptSeverity.CRITICAL
    assert classify_attempt_severity(attempt, Mode.RESERVATION) == AttemptSeverity.MODERATE


def test_an_unconfirmed_reservation_is_ambiguous_not_clean():
    """table_available=True but reservation_confirmed=False -- a table may
    genuinely be held pending confirmation, unlike a flat 'no table'."""
    attempt = {"passed": 0, "status": "COMPLETED", "rejection_reason": "Reservation was not confirmed"}
    assert classify_attempt_severity(attempt, Mode.RESERVATION) == AttemptSeverity.MODERATE


# --------------------------------------------------------------------------
# build_correction_call_goal() -- privacy, mandate, ordering
# --------------------------------------------------------------------------

def test_the_rendered_correction_goal_never_mentions_order_details_even_when_set(monkeypatch):
    """Privacy by construction: these fields ARE set on the request, as a
    stress test, and must still never appear -- build_correction_call_goal()
    must not simply happen to not read them today, it must be structurally
    unable to leak them."""
    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    request = _correction_request(
        Mode.DELIVERY,
        food_prompt="2x Pizza Margherita, extra cheese",
        delivery_address="Musterstrasse 1, 12345 Berlin",
        max_budget_eur=987.65,
        max_booking_fee_eur=42.0,
    )
    goal = build_call_goal(RESTAURANT, request)
    assert "Pizza" not in goal
    assert "Margherita" not in goal
    assert "Musterstrasse" not in goal
    assert "12345" not in goal
    assert "987" not in goal
    assert "42.0" not in goal and "42.00" not in goal
    # The requester's name IS disclosed -- that is the point of the intro.
    assert "Erika Musterfrau" in goal


def test_the_rendered_correction_goal_discloses_nothing_beyond_the_requester_name_in_german(monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, "de")
    request = _correction_request(
        Mode.RESERVATION,
        food_prompt="",
        delivery_address="Musterstrasse 1, 12345 Berlin",
        party_size=99,
    )
    goal = build_call_goal(RESTAURANT, request)
    assert "Musterstrasse" not in goal
    assert "99" not in goal
    assert "Erika Musterfrau" in goal


def test_self_reference_comes_before_the_mandate_clause_and_the_question(monkeypatch):
    """The R21 privacy-order pattern (ringedingeding commits f23aa2b/
    a8d2099): the self-reference sentence must be the FIRST substantive
    content of the returned text (right after the mandatory AI-disclosure
    preamble that every CALL-E goal opens with), before the mandate limit
    and before the actual question."""
    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    request = _correction_request(Mode.DELIVERY)
    goal = build_call_goal(RESTAURANT, request)
    assert goal.startswith("Hello, this is an automated assistant.")
    intro_idx = goal.index("I already called this restaurant once today")
    mandate_idx = goal.index("This call is NOT a new order")
    question_idx = goal.index("no order was actually placed")
    assert intro_idx < 50  # immediately after the disclosure, nothing else precedes it
    assert intro_idx < mandate_idx < question_idx


@pytest.mark.parametrize("mode", [Mode.DELIVERY, Mode.PICKUP, Mode.RESERVATION])
def test_the_mandate_clause_rules_out_a_new_order_or_reservation_in_english(mode, monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    goal = build_call_goal(RESTAURANT, _correction_request(mode))
    assert "This call is NOT a new order and NOT a new reservation" in goal


@pytest.mark.parametrize("mode", [Mode.DELIVERY, Mode.PICKUP, Mode.RESERVATION])
def test_the_mandate_clause_rules_out_a_new_order_or_reservation_in_german(mode, monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, "de")
    goal = build_call_goal(RESTAURANT, _correction_request(mode))
    assert "Dieser Anruf ist KEINE neue Bestellung und KEINE neue Reservierung" in goal


def test_the_reservation_correction_goal_asks_about_a_table_not_an_order(monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    goal = build_call_goal(RESTAURANT, _correction_request(Mode.RESERVATION))
    assert "no table was actually reserved" in goal


# --------------------------------------------------------------------------
# Idempotency (R20): never reuse the original attempt's key
# --------------------------------------------------------------------------

def test_a_correction_calls_idempotency_key_never_collides_with_the_original_R20():
    ts = 1_700_000_000.0
    original = generate_idempotency_key(Mode.DELIVERY.value, "rest_1", ts)
    correction = generate_idempotency_key(f"correction-{Mode.DELIVERY.value}", "rest_1", ts)
    assert original != correction
    # Same restaurant, same 5-minute bucket, same original mode string --
    # the ONLY thing that differs is the "correction-" prefix, and that
    # alone must already be enough.
    same_bucket_retry = generate_idempotency_key(Mode.DELIVERY.value, "rest_1", ts + 1)
    assert original == same_bucket_retry  # sanity: same bucket really does collide normally
    assert correction != same_bucket_retry


# --------------------------------------------------------------------------
# The manual-trigger-only web route
# --------------------------------------------------------------------------

def _seed_critical_delivery_attempt(order_id: str = "ord_e41", restaurant_id: str = "rest_e41"):
    create_order_record(
        order_id=order_id,
        mode="delivery",
        customer_name="Erika Musterfrau",
        food_prompt="2x Pizza",
        dry_run=True,
    )
    attempt = record_call_attempt(
        order_id=order_id,
        restaurant_id=restaurant_id,
        restaurant_name="Pizzeria Test",
        run_id="run_original",
        status="COMPLETED",
        passed=False,
        rejection_reason="Confirmed booking fee 5.00 EUR exceeds the authorised maximum of 0.00 EUR",
        post_summary="Restaurant agreed to a fee we could not authorise.",
        transcript="[masked]",
        live=False,
        restaurant_phone="+4910004069002",
    )
    return attempt["id"]


def test_a_critical_attempt_gets_a_correction_call_and_a_new_linked_row(client):
    attempt_id = _seed_critical_delivery_attempt()

    response = client.post("/api/correction-call?lang=en", data={"attempt_id": attempt_id})

    assert response.status_code == 200
    assert "Confirmed: nothing was placed." in response.text

    attempts = list_call_attempts("ord_e41")
    assert len(attempts) == 2
    correction_row = next(a for a in attempts if a["id"] != attempt_id)
    assert correction_row["corrects_attempt_id"] == attempt_id
    assert correction_row["restaurant_id"] == "rest_e41"


def test_a_clean_decline_refuses_a_correction_call_and_writes_nothing(client):
    create_order_record(
        order_id="ord_clean", mode="delivery", customer_name="Erika Musterfrau",
        food_prompt="2x Pizza", dry_run=True,
    )
    attempt = record_call_attempt(
        order_id="ord_clean", restaurant_id="rest_clean", restaurant_name="Pizzeria Clean",
        run_id="run_clean", status="COMPLETED", passed=False,
        rejection_reason="Restaurant does not deliver to specified address",
        post_summary="", transcript="", live=False, restaurant_phone="+4910004069003",
    )

    response = client.post("/api/correction-call?lang=en", data={"attempt_id": attempt["id"]})

    assert response.status_code == 200
    assert "Correction call failed." in response.text
    assert len(list_call_attempts("ord_clean")) == 1


def test_a_correction_call_cannot_itself_be_corrected_again(client):
    attempt_id = _seed_critical_delivery_attempt("ord_chain", "rest_chain")
    first = client.post("/api/correction-call?lang=en", data={"attempt_id": attempt_id})
    assert "Confirmed: nothing was placed." in first.text
    correction_id = get_call_attempt(attempt_id)  # unchanged; find the new row instead
    new_row = next(a for a in list_call_attempts("ord_chain") if a["id"] != attempt_id)

    second = client.post("/api/correction-call?lang=en", data={"attempt_id": new_row["id"]})

    assert "Correction call failed." in second.text
    assert len(list_call_attempts("ord_chain")) == 2  # no third row appeared
    assert correction_id is not None  # original attempt untouched


def test_a_legacy_row_without_a_stored_phone_number_cannot_be_corrected(client):
    create_order_record(
        order_id="ord_legacy", mode="delivery", customer_name="Erika Musterfrau",
        food_prompt="2x Pizza", dry_run=True,
    )
    attempt = record_call_attempt(
        order_id="ord_legacy", restaurant_id="rest_legacy", restaurant_name="Pizzeria Legacy",
        run_id="run_legacy", status="COMPLETED", passed=False,
        rejection_reason="Confirmed booking fee 5.00 EUR exceeds the authorised maximum of 0.00 EUR",
        post_summary="", transcript="", live=False,
        # restaurant_phone intentionally omitted -- a row from before E41.
    )

    response = client.post("/api/correction-call?lang=en", data={"attempt_id": attempt["id"]})

    assert response.status_code == 200
    assert "No phone number on file for a correction call." in response.text
    assert len(list_call_attempts("ord_legacy")) == 1
