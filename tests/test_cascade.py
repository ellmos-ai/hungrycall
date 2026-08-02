"""Integration tests for sequential cascade execution across modes."""

from hungrycall.models import Mode, UserRequest
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.call_client import DryRunCallClient
from hungrycall.engine import CascadeEngine


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


def test_tiered_concessions_cascade():
    """Verify tiered concessions negotiation cascade (MUSTER.md pattern)."""
    req = UserRequest(
        mode=Mode.RESERVATION,
        customer_name="Alex",
        food_prompt="Italian",
        reservation_date="2026-08-05",
        reservation_time="19:00",
        party_size=4
    )
    
    client = DryRunCallClient(scenario_name="tiered_concessions_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)
    
    summary = engine.run(req)
    
    assert summary.success is True
    assert summary.successful_restaurant.id == "rest_trattoria_luigi"
    assert summary.final_result.structured_result.get("tier_applied") == "tier_2_concession_fee"
    assert "Table reserved at Trattoria Bella Luigi" in summary.message
    assert "via Tier 2" in summary.final_result.post_summary


