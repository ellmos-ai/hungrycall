"""Scenario matrix for the generated goal text: "what must the text actually say?"

Companion to CONVERSATION-TREE.md — every scenario here is one path through that
document's tree, and every substring assertion cites the section (§) that names
the fragment it is checking. Two complementary checks run per scenario:

1. **Substring/order assertions** (``CHECKS``): the specific fragments this
   scenario must contain, and — where order matters (e.g. the chain must be
   worked through before any total-price question) — in what order.
2. **Golden files** (``tests/goldens/<scenario>.<lang>.txt``): the complete
   expected goal text, so ANY change to the wording is a visible, reviewable
   diff, not just a silent pass/fail on the substrings above.

Golden files are never written by this test file or by pytest. Regenerate them
explicitly and deliberately with::

    python tests/goldens/regenerate.py

which prints a diff-like summary of what changed and requires the changes to be
reviewed before they are committed — a red pytest run must never be "fixed" by
silently overwriting the goldens it disagrees with.

Scope note on the matrix: concessions (``_concession_clause``) are a single,
self-contained builder independent of the order-chain machinery, so they are
exercised on representative delivery/pickup bases (scenarios 2-3) rather than
crossed with every chain variant — CONVERSATION-TREE.md §4 row 12 documents
that the concession mechanism is not reachable from the web UI at all today,
which is exactly why this suite drives it directly through ``UserRequest``
instead of through a form.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from hungrycall.call_language import CALL_LOCALE_ENV
from hungrycall.engine import build_call_goal
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.models import (
    Concession,
    Mode,
    OrderChain,
    Seating,
    UserRequest,
)

RESTAURANT = SAMPLE_RESTAURANTS[0]  # build_call_goal never reads restaurant fields
CALLBACK = "+4910004069000"  # fictional throughout (AGENTS.md); matches other test files
GOLDENS_DIR = Path(__file__).parent / "goldens"
LANGUAGES = ("de", "en")


# --------------------------------------------------------------------------
# Request builders
# --------------------------------------------------------------------------

def _delivery(**overrides) -> UserRequest:
    base = {
        "mode": Mode.DELIVERY,
        "customer_name": "Alex Beispiel",
        "first_name": "Alex",
        "last_name": "Beispiel",
        "food_prompt": "Burger",
        "max_budget_eur": 25.0,
        "delivery_address": "Musterstrasse 5, 12345 Dorfstadt",
        "requester_callback_number": CALLBACK,
    }
    base.update(overrides)
    return UserRequest(**base)


def _pickup(**overrides) -> UserRequest:
    base = {
        "mode": Mode.PICKUP,
        "customer_name": "Alex Beispiel",
        "first_name": "Alex",
        "last_name": "Beispiel",
        "food_prompt": "Pizza",
        "max_budget_eur": 20.0,
        "pickup_time": "19:30",
        "requester_callback_number": CALLBACK,
    }
    base.update(overrides)
    return UserRequest(**base)


def _reservation(**overrides) -> UserRequest:
    base = {
        "mode": Mode.RESERVATION,
        "customer_name": "Alex Beispiel",
        "first_name": "Alex",
        "last_name": "Beispiel",
        "food_prompt": "Italian",
        "reservation_date": "2026-08-07",
        "reservation_time": "19:00",
        "party_size": 4,
        "requester_callback_number": CALLBACK,
    }
    base.update(overrides)
    return UserRequest(**base)


def _cell(product: str, quantity: int = 1, kind: str = "essen", criteria=None) -> dict:
    return {"menge": quantity, "produkt": product, "art": kind, "kriterien": criteria or []}


def _criterion(kind: str, value, on_yes: str = "annehmen", on_no: str = "naechster_ersatz") -> dict:
    return {"art": kind, "wert": value, "reaktion_ja": on_yes, "reaktion_nein": on_no}


def _chain(*positions: dict) -> OrderChain:
    return OrderChain.from_dict({"version": 1, "posten": list(positions)})


def _position(*cells: dict, tags: list[str] | None = None, end_rule: str = "posten_weglassen") -> dict:
    return {"zellen": list(cells), "tags": tags or [], "wenn_nichts_verfuegbar": end_rule}


# --------------------------------------------------------------------------
# Scenario matrix: name -> (request factory, substring/order checks)
#
# Each check function receives (goal_text, lang) and asserts. ``lang`` lets a
# check assert the LANGUAGE-CORRECT fragment (e.g. "Haben Sie" in de, "Do you
# have" in en) instead of hard-coding German everywhere.
# --------------------------------------------------------------------------

Check = Callable[[str, str], None]


def _delivery_simple() -> UserRequest:
    return _delivery()


def _check_delivery_simple(goal: str, lang: str) -> None:
    # §1.1: delivery/address check and the total-price question share the
    # same numbered list in the simple (non-chain) path.
    assert "Musterstrasse 5, 12345 Dorfstadt" in goal
    assert "Requested items: 'Burger'" in goal
    assert "25.00 EUR" in goal
    assert goal.index("Do you deliver to this address") < goal.index("EXACT total price")
    assert "order_chain" not in goal.lower() and "Position 1" not in goal


def _delivery_concession_one() -> UserRequest:
    return _delivery(concessions=[
        Concession(key="cash_ok", label="a cash-only payment is acceptable", tier=1),
    ])


def _check_delivery_concession_one(goal: str, lang: str) -> None:
    # §2.6: a single concession still renders the full fallback-ladder shape.
    assert "Step 1: only if the previous attempt failed, a cash-only payment is acceptable" in goal
    assert "'cash_ok'" in goal
    assert "Do not offer anything beyond what is stated above" not in goal


def _delivery_concession_many() -> UserRequest:
    return _delivery(concessions=[
        Concession(key="later_ok", label="a later delivery slot is acceptable", tier=2),
        Concession(key="cash_ok", label="a cash-only payment is acceptable", tier=1),
    ])


def _check_delivery_concession_many(goal: str, lang: str) -> None:
    # §2.6: concessions are re-sorted by tier regardless of input order, and
    # the ladder must never reveal a later step before an earlier one.
    assert goal.index("cash-only payment") < goal.index("later delivery slot")
    assert "Step 1: only if the previous attempt failed, a cash-only payment is acceptable" in goal
    assert "Step 2: only if the previous attempt failed, a later delivery slot is acceptable" in goal
    assert "'cash_ok', 'later_ok'" in goal


def _delivery_chain_max_price() -> UserRequest:
    chain = _chain(_position(_cell(
        "Pasta Napoli",
        criteria=[_criterion("hoechstpreis", 9.5)],
    )))
    return _delivery(order_chain=chain, food_prompt=chain.summary())


def _check_delivery_chain_max_price(goal: str, lang: str) -> None:
    # §2.2: hoechstpreis renders the exact-unit-price question with the
    # numeric ceiling interpolated, not the criterion's raw config value.
    assert "9.50 EUR" in goal
    assert "ask for the exact unit price" in goal
    # §1.1: the instruction not to ask for a total price before the chain is
    # settled precedes the chain body itself; the conditioned permission to
    # ask ("Only after the items are settled...") is part of that same
    # opening instruction, not something that only appears once the chain
    # text starts — so it is the PROHIBITION, not the word "total price"
    # itself, whose position relative to "Position 1" matters here.
    assert goal.index("do not ask for any total price before the items are settled") < goal.index("Position 1")


def _delivery_chain_special_request() -> UserRequest:
    chain = _chain(_position(_cell(
        "Pizza Margherita",
        criteria=[_criterion("sonderwunsch", "glutenfrei")],
    )))
    return _delivery(order_chain=chain, food_prompt=chain.summary())


def _check_delivery_chain_special_request(goal: str, lang: str) -> None:
    # §2.2: sonderwunsch quotes the free-text wish but is not itself
    # spoken verbatim (no "ask exactly").
    assert "ask whether 'glutenfrei' can be fulfilled" in goal
    assert 'ask exactly "glutenfrei"' not in goal


def _delivery_chain_question() -> UserRequest:
    chain = _chain(_position(_cell(
        "Salat",
        criteria=[_criterion("rueckfrage", "Ist der Salat vegan?")],
    )))
    return _delivery(order_chain=chain, food_prompt=chain.summary())


def _check_delivery_chain_question(goal: str, lang: str) -> None:
    # §2.2: rueckfrage IS spoken verbatim ("ask exactly ...").
    assert 'ask exactly "Ist der Salat vegan?"' in goal


def _delivery_chain_skip_rule() -> UserRequest:
    chain = _chain(_position(_cell("Tiramisu"), end_rule="posten_weglassen"))
    return _delivery(order_chain=chain, food_prompt=chain.summary())


def _check_delivery_chain_skip_rule(goal: str, lang: str) -> None:
    # §2.4: skip rule allows the cascade to continue to a total-price
    # question once every position has resolved.
    assert "this item is dropped" in goal
    assert "the whole order is off" not in goal


def _delivery_chain_abort_rule() -> UserRequest:
    chain = _chain(_position(_cell("Tiramisu"), end_rule="bestellung_abbrechen"))
    return _delivery(order_chain=chain, food_prompt=chain.summary())


def _check_delivery_chain_abort_rule(goal: str, lang: str) -> None:
    # §2.4: the abort rule forbids the total-price question outright — this
    # is the exact 2026-08-11 field-trial defect (FINDINGS.md).
    assert "the whole order is off" in goal
    assert "do NOT ask for any total price" in goal
    assert "this item is dropped" not in goal


def _delivery_chain_multi_position() -> UserRequest:
    # Tag values deliberately do not collide with anything else the goal
    # legitimately contains (the default customer_name is "Alex Beispiel").
    chain = _chain(
        _position(_cell("Burger", quantity=2), tags=["urgent"]),
        _position(_cell("Pommes"), tags=["urgent", "side-dish"]),
    )
    return _delivery(order_chain=chain, food_prompt=chain.summary())


def _check_delivery_chain_multi_position(goal: str, lang: str) -> None:
    # §2, §2.5: positions are worked in order. Tags do NOT reach the prompt
    # (CONVERSATION-TREE.md §4 row 20, fixed) -- they exist only for the
    # result screen's grouping (render_tag_summary), read from
    # position.tags directly, never parsed back out of this text.
    assert goal.index("Position 1") < goal.index("Position 2")
    assert "tags" not in goal.lower()
    assert "urgent" not in goal  # the tag values themselves must not leak either
    assert "side-dish" not in goal
    assert "order 2 x Burger for this position" in goal


def _pickup_simple() -> UserRequest:
    return _pickup()


def _check_pickup_simple(goal: str, lang: str) -> None:
    assert "Preferred pickup time: 19:30" in goal
    assert "do you offer pickup orders, and are you currently open" in goal
    assert "Requested items: 'Pizza'" in goal


def _pickup_chain() -> UserRequest:
    chain = _chain(_position(_cell("Pizza Margherita")))
    return _pickup(order_chain=chain, food_prompt=chain.summary())


def _check_pickup_chain(goal: str, lang: str) -> None:
    # Coverage-map finding #3b (CONVERSATION-TREE.md §4 row 3b, fixed): pickup
    # used to keep the food_prompt/summary line AND append the full chain
    # afterwards, redundant with delivery+chain which already dropped it.
    # Pickup now matches delivery's structure: no Requested-items line, and
    # the total-price question deferred until after the chain is settled.
    assert "Requested items:" not in goal
    assert "Position 1" in goal
    assert "There is no delivery fee, we collect ourselves" in goal
    assert goal.index("do not ask for any total price before the items are settled") < goal.index("Position 1")


def _reservation_no_tolerances() -> UserRequest:
    return _reservation()


def _check_reservation_no_tolerances(goal: str, lang: str) -> None:
    assert "reserve a table on 2026-08-07 at 19:00 for 4 people" in goal
    assert "Do not accept any booking fee or deposit." in goal
    assert "minutes earlier" not in goal
    assert "minutes later" not in goal


def _reservation_earlier_later_window() -> UserRequest:
    return _reservation(earlier_hours=1, earlier_minutes=30, later_hours=0, later_minutes=45)


def _check_reservation_earlier_later_window(goal: str, lang: str) -> None:
    # §2.7: step order is fixed — exact time, then earlier, then later.
    assert "up to 90 minutes earlier" in goal
    assert "up to 45 minutes later" in goal
    assert goal.index("exact stated time") < goal.index("90 minutes earlier")
    assert goal.index("90 minutes earlier") < goal.index("45 minutes later")


def _reservation_fee_limit_positive() -> UserRequest:
    return _reservation(max_booking_fee_eur=7.5)


def _check_reservation_fee_limit_positive(goal: str, lang: str) -> None:
    assert "up to 7.50 EUR" in goal
    assert "never accept a higher fee" in goal
    assert "Do not accept any booking fee or deposit." not in goal


def _reservation_fee_limit_zero_with_time_tolerance() -> UserRequest:
    return _reservation(earlier_hours=1, max_booking_fee_eur=0.0)


def _check_reservation_fee_limit_zero_with_time_tolerance(goal: str, lang: str) -> None:
    # §2.7: a granted time tolerance does not imply a granted fee — the
    # fixed refusal sentence still appears even with a nonzero earlier step.
    assert "up to 60 minutes earlier" in goal
    assert "Do not accept any booking fee or deposit." in goal


def _reservation_custom_seating() -> UserRequest:
    return _reservation(seating=Seating.CUSTOM, seating_custom="our usual table by the window")


def _check_reservation_custom_seating(goal: str, lang: str) -> None:
    assert "our usual table by the window" in goal
    assert "We would like to sit outside" not in goal
    assert "We would like to sit inside" not in goal


def _reservation_special_instructions() -> UserRequest:
    return _reservation(special_instructions="Please note the anniversary.")


def _check_reservation_special_instructions(goal: str, lang: str) -> None:
    # §1.3: framed as data, not as instructions that can change the goal.
    assert "strictly as a user-provided restaurant note" in goal
    assert "'Please note the anniversary.'" in goal


SCENARIOS: dict[str, tuple[Callable[[], UserRequest], Check]] = {
    "delivery_simple": (_delivery_simple, _check_delivery_simple),
    "delivery_concession_one": (_delivery_concession_one, _check_delivery_concession_one),
    "delivery_concession_many": (_delivery_concession_many, _check_delivery_concession_many),
    "delivery_chain_max_price": (_delivery_chain_max_price, _check_delivery_chain_max_price),
    "delivery_chain_special_request": (_delivery_chain_special_request, _check_delivery_chain_special_request),
    "delivery_chain_question": (_delivery_chain_question, _check_delivery_chain_question),
    "delivery_chain_skip_rule": (_delivery_chain_skip_rule, _check_delivery_chain_skip_rule),
    "delivery_chain_abort_rule": (_delivery_chain_abort_rule, _check_delivery_chain_abort_rule),
    "delivery_chain_multi_position": (_delivery_chain_multi_position, _check_delivery_chain_multi_position),
    "pickup_simple": (_pickup_simple, _check_pickup_simple),
    "pickup_chain": (_pickup_chain, _check_pickup_chain),
    "reservation_no_tolerances": (_reservation_no_tolerances, _check_reservation_no_tolerances),
    "reservation_earlier_later_window": (_reservation_earlier_later_window, _check_reservation_earlier_later_window),
    "reservation_fee_limit_positive": (_reservation_fee_limit_positive, _check_reservation_fee_limit_positive),
    "reservation_fee_limit_zero_with_time_tolerance": (
        _reservation_fee_limit_zero_with_time_tolerance,
        _check_reservation_fee_limit_zero_with_time_tolerance,
    ),
    "reservation_custom_seating": (_reservation_custom_seating, _check_reservation_custom_seating),
    "reservation_special_instructions": (_reservation_special_instructions, _check_reservation_special_instructions),
}


def _language_checks(goal: str, lang: str) -> None:
    """Every scenario, every language: the OTHER language's mandatory
    verbatim sentences must never leak in (the exact 2026-08-11 field-trial
    defect this suite exists to pin down)."""
    if lang == "de":
        assert "Hallo, hier spricht ein automatisierter Assistent" in goal
        assert "Conduct the entire conversation in German" in goal
        assert "Hello, this is an automated assistant" not in goal
        assert "Conduct the entire conversation in English" not in goal
    else:
        assert "Hello, this is an automated assistant" in goal
        assert "Conduct the entire conversation in English" in goal
        assert "Hallo, hier spricht ein automatisierter Assistent" not in goal
        assert "Conduct the entire conversation in German" not in goal


def _build_goal(scenario_name: str, lang: str, monkeypatch) -> str:
    monkeypatch.setenv(CALL_LOCALE_ENV, lang)
    factory, _check = SCENARIOS[scenario_name]
    return build_call_goal(RESTAURANT, factory())


@pytest.mark.parametrize("scenario_name", sorted(SCENARIOS))
@pytest.mark.parametrize("lang", LANGUAGES)
def test_scenario_substrings_and_order(scenario_name: str, lang: str, monkeypatch):
    goal = _build_goal(scenario_name, lang, monkeypatch)
    _language_checks(goal, lang)
    _, check = SCENARIOS[scenario_name]
    check(goal, lang)


@pytest.mark.parametrize("scenario_name", sorted(SCENARIOS))
@pytest.mark.parametrize("lang", LANGUAGES)
def test_scenario_matches_golden_file(scenario_name: str, lang: str, monkeypatch):
    goal = _build_goal(scenario_name, lang, monkeypatch)
    golden_path = GOLDENS_DIR / f"{scenario_name}.{lang}.txt"
    if not golden_path.exists():
        pytest.fail(
            f"No golden file for '{scenario_name}.{lang}'. Generate it with "
            f"'python tests/goldens/regenerate.py' and review the diff before committing."
        )
    expected = golden_path.read_text(encoding="utf-8")
    assert goal == expected, (
        f"Goal text for '{scenario_name}.{lang}' no longer matches its golden file.\n"
        f"If this change is intentional, review it and regenerate with "
        f"'python tests/goldens/regenerate.py'.\n"
        f"--- golden ({golden_path.name}) ---\n{expected}\n"
        f"--- actual ---\n{goal}\n"
    )


# --------------------------------------------------------------------------
# Flip tests: two settings that must produce DIFFERENT, and only different,
# text — not covered by a single scenario's own checks above.
# --------------------------------------------------------------------------

def test_flip_position_end_rule_produces_different_text(monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    skip_goal = build_call_goal(RESTAURANT, _delivery_chain_skip_rule())
    abort_goal = build_call_goal(RESTAURANT, _delivery_chain_abort_rule())
    assert skip_goal != abort_goal
    assert "this item is dropped" in skip_goal and "this item is dropped" not in abort_goal
    assert "the whole order is off" in abort_goal and "the whole order is off" not in skip_goal


def test_flip_criterion_reaction_reject_vs_next_replacement(monkeypatch):
    """CONVERSATION-TREE.md §2.3: 'ablehnen' and 'naechster_ersatz' must
    render as distinct, opposite instructions for the same criterion."""
    from hungrycall.order_chains import build_order_chain_instruction

    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    reject_chain = _chain(_position(_cell(
        "Burger", criteria=[_criterion("hoechstpreis", 8.0, on_no="ablehnen")],
    )))
    replace_chain = _chain(_position(_cell(
        "Burger", criteria=[_criterion("hoechstpreis", 8.0, on_no="naechster_ersatz")],
    )))
    reject_text = build_order_chain_instruction(reject_chain)
    replace_text = build_order_chain_instruction(replace_chain)

    assert reject_text != replace_text
    assert "reject this position immediately" in reject_text
    assert "reject this position immediately" not in replace_text
    assert "discard this cell and try the next replacement cell" in replace_text
    assert "discard this cell and try the next replacement cell" not in reject_text


def test_flip_reservation_step_numbering_shifts_with_granted_tolerances(monkeypatch):
    """CONVERSATION-TREE.md §2.7: only later (no earlier) still numbers as
    Step 2, not Step 3 — the step counter tracks what was actually granted,
    not a fixed slot per tolerance kind."""
    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    later_only = build_call_goal(RESTAURANT, _reservation(later_hours=1))
    assert "Step 2: only if every earlier authorised option failed" in later_only
    assert "up to 60 minutes later" in later_only
    assert "minutes earlier" not in later_only


# --------------------------------------------------------------------------
# Per-mode x per-language opening sentence: isolated so a change to any
# mode's own opening cannot hide inside a larger scenario's golden diff.
# --------------------------------------------------------------------------

OPENERS = {
    ("delivery", "de"): (_delivery_simple, "We would like to order food for delivery to"),
    ("delivery", "en"): (_delivery_simple, "We would like to order food for delivery to"),
    ("pickup", "de"): (_pickup_simple, "We would like to place a pickup order to collect in person"),
    ("pickup", "en"): (_pickup_simple, "We would like to place a pickup order to collect in person"),
    ("reservation", "de"): (_reservation_no_tolerances, "We would like to reserve a table on"),
    ("reservation", "en"): (_reservation_no_tolerances, "We would like to reserve a table on"),
}


@pytest.mark.parametrize("mode,lang", list(OPENERS))
def test_mode_opening_sentence_per_language(mode: str, lang: str, monkeypatch):
    factory, expected_opener = OPENERS[(mode, lang)]
    monkeypatch.setenv(CALL_LOCALE_ENV, lang)
    goal = build_call_goal(RESTAURANT, factory())
    _language_checks(goal, lang)
    intro_end = goal.index("Prices must be recorded")
    assert expected_opener in goal[intro_end:intro_end + 400]
