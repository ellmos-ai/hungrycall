"""Unit tests for safety and policy guardrails."""

import pytest
from hungrycall.safety import (
    SafetyError, verify_content_safety, verify_phone_safety,
    verify_live_safety, generate_idempotency_key
)


def test_verify_content_safety_valid():
    verify_content_safety("2 Cheeseburger with fries")
    verify_content_safety("Table for 4 Italian food")


def test_verify_content_safety_prohibited_keywords():
    with pytest.raises(SafetyError) as exc_info:
        verify_content_safety("Call hospital emergency room")
    assert "Content safety policy violation" in str(exc_info.value)

    with pytest.raises(SafetyError):
        verify_content_safety("Order food from anwalt court")


def test_verify_phone_safety():
    verify_phone_safety("+441632960090")
    
    with pytest.raises(SafetyError):
        verify_phone_safety("07700900090")


def test_verify_live_safety():
    verify_live_safety(live_flag=False, user_confirmed=False)  # Dry-run allowed
    verify_live_safety(live_flag=True, user_confirmed=True)   # Confirmed live allowed

    with pytest.raises(SafetyError):
        verify_live_safety(live_flag=True, user_confirmed=False)  # Unconfirmed live rejected


def test_generate_idempotency_key():
    key1 = generate_idempotency_key("delivery", "rest_123", 1000.0)
    key2 = generate_idempotency_key("delivery", "rest_123", 1000.0)
    key3 = generate_idempotency_key("delivery", "rest_456", 1000.0)

    assert key1 == key2
    assert key1 != key3
    assert key1.startswith("hungrycall-delivery-rest_123-")
