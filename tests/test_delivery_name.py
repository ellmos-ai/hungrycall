"""A delivery must carry a full recipient name — the restaurant delivers to a person.

User feedback from the 2026-08-11 live field trial: the goal named the address but
never framed the requester as the delivery recipient, and the server accepted an
empty last name although the form marks it required.
"""

import pytest

from hungrycall.engine import build_call_goal
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.models import Mode
from hungrycall.web import build_user_request

BASE_FORM = {
    "mode": "delivery",
    "food_prompt": "2 Pizza Margherita",
    "max_budget_eur": "25",
    "delivery_address": "Musterstrasse 5, 12345 Dorfstadt",
    "first_name": "Alex",
    "last_name": "Beispiel",
    "requester_callback_number": "+447700900201",
}


def form(**overrides):
    data = dict(BASE_FORM)
    data.update(overrides)
    return data


def test_missing_last_name_is_rejected_server_side():
    with pytest.raises(ValueError, match="last_name"):
        build_user_request(form(last_name=""))


def test_delivery_goal_names_the_recipient_and_address():
    request = build_user_request(form())
    goal = build_call_goal(SAMPLE_RESTAURANTS[0], request)
    assert "The delivery is for Alex Beispiel" in goal
    assert "Musterstrasse 5, 12345 Dorfstadt" in goal


def test_pickup_goal_names_the_collector():
    request = build_user_request(
        form(mode="pickup", delivery_address="", pickup_time="19:30")
    )
    assert request.mode is Mode.PICKUP
    goal = build_call_goal(SAMPLE_RESTAURANTS[0], request)
    assert "collected by Alex Beispiel" in goal
