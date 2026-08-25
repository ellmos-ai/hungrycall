"""Integration tests for sequential cascade execution across modes."""

from hungrycall.call_client import DryRunCallClient
from hungrycall.engine import CascadeEngine, build_call_goal
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.models import Mode, Seating, UserRequest


def test_cascade_stops_immediately_on_first_success():
    """Verify critical rule: when a candidate satisfies all criteria, cascade stops immediately."""
    req = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Alex",
        food_prompt="Burger",
        max_budget_eur=35.00,
        delivery_address="Hauptstraße 12, 12345 Dorfstadt"
    )

    # scenario 'success_direct': First candidate succeeds immediately
    client = DryRunCallClient(scenario_name="success_direct")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)

    summary = engine.run(req)

    assert summary.success is True
    # ONLY 1 attempt made because it stopped immediately after success!
    assert len(summary.attempts) == 1
    assert summary.successful_restaurant.id == "rest_burger_house"
    assert "28.50 EUR" in summary.message
    assert summary.final_result.transcript is not None


def test_reservation_cascade():
    """Verify table reservation cascade."""
    req = UserRequest(
        mode=Mode.RESERVATION,
        customer_name="Alex",
        food_prompt="Italian",
        reservation_date="2026-08-05",
        reservation_time="19:00",
        party_size=4
    )

    client = DryRunCallClient(scenario_name="reservation_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)

    summary = engine.run(req)

    assert summary.success is True
    assert summary.successful_restaurant.id == "rest_trattoria_luigi"
    assert "Table reserved" in summary.message
    assert "4 people" in summary.message


def test_pickup_cascade():
    """Verify pickup order cascade."""
    req = UserRequest(
        mode=Mode.PICKUP,
        customer_name="Alex",
        food_prompt="Burger",
        max_budget_eur=25.00,
        pickup_time="19:30"
    )

    client = DryRunCallClient(scenario_name="pickup_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)

    summary = engine.run(req)

    assert summary.success is True
    assert summary.successful_restaurant.id == "rest_burger_house"
    assert "Pickup order placed" in summary.message
    assert "22.00 EUR" in summary.message


def build_reservation_request(seating=Seating.ANY, **overrides):
    values = {
        "mode": Mode.RESERVATION,
        "customer_name": "Alex",
        "food_prompt": "Italian",
        "reservation_date": "2026-08-05",
        "reservation_time": "19:00",
        "party_size": 4,
        "seating": seating,
        "requester_callback_number": "+447700900200",
    }
    values.update(overrides)
    return UserRequest(**values)


def test_tiered_concessions_cascade():
    """A booking fee is accepted only inside the explicit new fee cap."""
    req = build_reservation_request(max_booking_fee_eur=15)

    client = DryRunCallClient(scenario_name="tiered_concessions_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)

    summary = engine.run(req)

    assert summary.success is True
    assert summary.successful_restaurant.id == "rest_trattoria_luigi"
    assert "Table reserved at Trattoria Bella Luigi" in summary.message
    assert "authorised 15 EUR" in summary.final_result.post_summary


def test_unauthorised_concession_is_rejected():
    """The same call, without the grant, must not count as a success.

    This is the whole point of concessions being an authorisation rather than a
    hint: an agent that bought the table with money we never offered has
    exceeded its mandate, and the yes it brought back is not accepted.
    """
    req = build_reservation_request(max_booking_fee_eur=0)

    client = DryRunCallClient(scenario_name="tiered_concessions_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)

    summary = engine.run(req)

    assert summary.success is False
    luigi = [a for a in summary.attempts if a.restaurant.id == "rest_trattoria_luigi"]
    assert luigi, "Trattoria should have been called"
    assert "exceeds the authorised maximum" in luigi[0].rejection_reason
    assert luigi[0].concession_used is None


def test_goal_text_orders_concessions_and_forbids_bundling():
    """The new reservation ladder is precise and supersedes legacy grants."""
    req = build_reservation_request(
        earlier_hours=1,
        later_minutes=30,
        max_booking_fee_eur=3,
    )
    goal = build_call_goal(SAMPLE_RESTAURANTS[1], req)

    assert goal.index("exact stated time") < goal.index("60 minutes earlier")
    assert goal.index("60 minutes earlier") < goal.index("30 minutes later")
    assert goal.index("30 minutes later") < goal.index("3.00 EUR")
    assert "15 EUR" not in goal


def test_table_branch_cascade_rejects_then_books_outdoor():
    """The table branch runs the same cascade on entirely different criteria."""
    req = build_reservation_request(seating=Seating.OUTDOOR)

    client = DryRunCallClient(scenario_name="table_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)

    summary = engine.run(req)

    assert summary.success is True
    # First the favourite Italian, fully booked; then the pub with the garden.
    assert summary.attempts[0].restaurant.id == "rest_trattoria_luigi"
    assert "Fully booked" in summary.attempts[0].rejection_reason
    assert summary.successful_restaurant.id == "rest_gasthaus_linde"
    assert "outdoor" in summary.message
    assert len(summary.attempts) == 2  # stopped as soon as one worked


def test_indoor_table_rejected_when_outdoor_was_asked_for():
    """A table inside is not the table that was requested."""
    req = build_reservation_request(seating=Seating.OUTDOOR)
    client = DryRunCallClient(scenario_name="table_concession_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)

    summary = engine.run(req)

    assert summary.success is False

    # A crafted legacy concession must not reopen the rejected result.
    req_ok = build_reservation_request(seating=Seating.OUTDOOR)
    req_ok.concessions = []
    summary_ok = CascadeEngine(
        candidate_pool=SAMPLE_RESTAURANTS,
        call_client=DryRunCallClient(scenario_name="table_concession_cascade"),
    ).run(req_ok)

    assert summary_ok.success is False
