"""Integration tests for sequential cascade execution across modes."""

from hungrycall.models import Concession, Mode, Seating, UserRequest
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.call_client import DryRunCallClient
from hungrycall.engine import CascadeEngine, build_call_goal


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


DEPOSIT_CONCESSION = Concession(
    key="tier_2_concession_fee",
    label="a booking deposit of up to 15 EUR is acceptable",
    tier=2,
)


def build_reservation_request(concessions=None, seating=Seating.ANY):
    return UserRequest(
        mode=Mode.RESERVATION,
        customer_name="Alex",
        food_prompt="Italian",
        reservation_date="2026-08-05",
        reservation_time="19:00",
        party_size=4,
        seating=seating,
        concessions=concessions or [],
    )


def test_tiered_concessions_cascade():
    """A concession the user granted may be played, and is reported as used."""
    req = build_reservation_request(concessions=[DEPOSIT_CONCESSION])

    client = DryRunCallClient(scenario_name="tiered_concessions_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)

    summary = engine.run(req)

    assert summary.success is True
    assert summary.successful_restaurant.id == "rest_trattoria_luigi"
    assert summary.concession_used == "tier_2_concession_fee"
    assert summary.attempts[-1].concession_used == "tier_2_concession_fee"
    assert "Table reserved at Trattoria Bella Luigi" in summary.message
    assert "via Tier 2" in summary.final_result.post_summary


def test_unauthorised_concession_is_rejected():
    """The same call, without the grant, must not count as a success.

    This is the whole point of concessions being an authorisation rather than a
    hint: an agent that bought the table with money we never offered has
    exceeded its mandate, and the yes it brought back is not accepted.
    """
    req = build_reservation_request(concessions=[])

    client = DryRunCallClient(scenario_name="tiered_concessions_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)

    summary = engine.run(req)

    assert summary.success is False
    luigi = [a for a in summary.attempts if a.restaurant.id == "rest_trattoria_luigi"]
    assert luigi, "Trattoria should have been called"
    assert "not authorised" in luigi[0].rejection_reason
    assert luigi[0].concession_used is None


def test_goal_text_orders_concessions_and_forbids_bundling():
    """The goal text must hand over the order, not just the list."""
    req = build_reservation_request(
        concessions=[
            Concession(key="indoor_ok", label="an indoor table is acceptable", tier=1),
            DEPOSIT_CONCESSION,
        ]
    )
    goal = build_call_goal(SAMPLE_RESTAURANTS[1], req)

    assert goal.index("Step 1: ") < goal.index("Step 2: ")
    assert "an indoor table is acceptable" in goal
    assert "Never offer a later step before an earlier one has failed" in goal
    assert "'indoor_ok', 'tier_2_concession_fee'" in goal


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

    # ...but with the concession granted, the very same call is a success.
    req_ok = build_reservation_request(
        seating=Seating.OUTDOOR,
        concessions=[Concession(key="indoor_ok", label="an indoor table is acceptable", tier=1)],
    )
    summary_ok = CascadeEngine(
        candidate_pool=SAMPLE_RESTAURANTS,
        call_client=DryRunCallClient(scenario_name="table_concession_cascade"),
    ).run(req_ok)

    assert summary_ok.success is True
    assert summary_ok.successful_restaurant.id == "rest_gasthaus_linde"
    assert summary_ok.concession_used == "indoor_ok"


