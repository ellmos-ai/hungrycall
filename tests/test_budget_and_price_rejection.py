"""Mandatory tests for HungryCall budget limit enforcement and vague price quote rejection."""

from hungrycall.models import Mode, UserRequest, CallStatus
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.call_client import DryRunCallClient
from hungrycall.engine import CascadeEngine


def test_budget_limit_exceeded_rejection():
    """Verify that a restaurant quote exceeding max_budget_eur is rejected, and cascade continues."""
    req = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Lukas",
        food_prompt="Burger",
        max_budget_eur=35.00,  # Limit is 35.00 EUR
        delivery_address="Hauptstraße 12, 12345 Dorfstadt"
    )
    
    # scenario 'budget_exceeded_cascade': First candidate quotes 42.00 EUR (exceeds 35.00 limit), second quotes 31.50 EUR
    client = DryRunCallClient(scenario_name="budget_exceeded_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)
    
    summary = engine.run(req)
    
    # Must succeed on second candidate after rejecting first
    assert summary.success is True
    assert len(summary.attempts) == 2
    
    # Attempt 1: Rejected due to budget limit
    attempt1 = summary.attempts[0]
    assert attempt1.passed_criteria is False
    assert "exceeds maximum budget limit of 35.00 EUR" in attempt1.rejection_reason
    assert attempt1.restaurant.id == "rest_burger_house"
    
    # Attempt 2: Accepted because 31.50 EUR <= 35.00 EUR
    attempt2 = summary.attempts[1]
    assert attempt2.passed_criteria is True
    assert attempt2.restaurant.id == "rest_trattoria_luigi"


def test_vague_price_quote_rejection():
    """Verify that price_known = False ('so ungefähr 30 Euro') leads to REJECTION instead of guessing."""
    req = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Lukas",
        food_prompt="Burger",
        max_budget_eur=35.00,
        delivery_address="Hauptstraße 12, 12345 Dorfstadt"
    )
    
    # scenario 'vague_price_cascade': First candidate price_known = False ("so ungefähr 30 Euro"), second candidate price_known = True (29.00 EUR)
    client = DryRunCallClient(scenario_name="vague_price_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)
    
    summary = engine.run(req)
    
    assert summary.success is True
    assert len(summary.attempts) == 2
    
    # Attempt 1: Rejected because price quote was vague / unconfirmed
    attempt1 = summary.attempts[0]
    assert attempt1.passed_criteria is False
    assert "Unclear price statement" in attempt1.rejection_reason
    assert attempt1.restaurant.id == "rest_burger_house"
    
    # Attempt 2: Accepted with exact price quote
    attempt2 = summary.attempts[1]
    assert attempt2.passed_criteria is True
    assert attempt2.restaurant.id == "rest_trattoria_luigi"


def test_strict_all_budget_exceeded_fails():
    """Verify that if ALL candidates exceed max_budget_eur, cascade fails cleanly without placing any order."""
    req = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Lukas",
        food_prompt="Burger",
        max_budget_eur=15.00,  # Very low budget limit: 15.00 EUR
        delivery_address="Hauptstraße 12, 12345 Dorfstadt"
    )
    
    client = DryRunCallClient(scenario_name="budget_exceeded_cascade")
    engine = CascadeEngine(candidate_pool=SAMPLE_RESTAURANTS, call_client=client)
    
    summary = engine.run(req)
    
    assert summary.success is False
    assert len(summary.attempts) >= 1
    for att in summary.attempts:
        assert att.passed_criteria is False
