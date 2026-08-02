"""Tests for the web interface, DB layer and location lookup.

The emphasis is on the things that used to only look like they worked: the
candidate order, the goal preview, the cancel button, the mode switch and the
saved result's mode.
"""

import json
import os

import pytest
from fastapi.testclient import TestClient

from hungrycall import web
from hungrycall.db import (
    create_order_record, init_db, list_saved_results, save_cascade_result
)
from hungrycall.location import (
    geocode_location, get_offline_restaurants, search_overpass_restaurants
)
from hungrycall.web import app


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Use an isolated temporary database for tests."""
    db_file = str(tmp_path / "test_hungrycall.db")
    os.environ["HUNGRYCALL_DB_PATH"] = db_file
    init_db(db_file)
    yield db_file
    os.environ.pop("HUNGRYCALL_DB_PATH", None)


@pytest.fixture(autouse=True)
def instant_cascade(monkeypatch):
    """Drop the simulated dialling delays so the stream tests finish quickly."""
    monkeypatch.setattr(web, "DRY_RUN_DIAL_SECONDS", 0)
    monkeypatch.setattr(web, "DRY_RUN_TURN_SECONDS", 0)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    """Freeze 'now' at Friday 19:00.

    Opening hours are checked against the real clock now, which is right and
    makes the tests depend on when they run. Freezing it here keeps that
    correctness without the flakiness.
    """
    monkeypatch.setattr(web, "current_clock", lambda: "19:00")
    monkeypatch.setattr(web, "current_day", lambda: "Fri")


@pytest.fixture
def client():
    return TestClient(app)


def sse_events(text):
    """Parse an SSE body into the list of decoded payloads."""
    return [
        json.loads(line[len("data: "):])
        for line in text.splitlines()
        if line.startswith("data: ")
    ]


def run_cascade(client, form):
    """Post a cascade form, then drain its stream. Returns (events, order_id)."""
    started = client.post("/api/start-cascade", data=form)
    assert started.status_code == 200
    order_id = started.text.split('HC.startStream("')[1].split('"')[0]
    stream = client.get(f"/api/cascade-stream?order_id={order_id}")
    return sse_events(stream.text), order_id


# --------------------------------------------------------------------------
# Storage and location
# --------------------------------------------------------------------------

def test_db_order_and_save_result(setup_test_db):
    order = create_order_record(
        order_id="test_ord_1",
        mode="delivery",
        customer_name="Lukas Test",
        food_prompt="Burger and Fries",
        max_budget_eur=30.0,
        delivery_address="Test Str 1, 12345 Dorfstadt",
    )
    assert order["id"] == "test_ord_1"

    saved = save_cascade_result(
        result_id="test_res_1",
        order_id="test_ord_1",
        mode="delivery",
        restaurant_id="rest_burger_house",
        restaurant_name="Burger House Dorfstadt",
        masked_phone="+49170...",
        callback_number="+491701111111",
        total_price_eur=28.50,
        eta_minutes=35,
        post_summary="Order confirmed successfully",
        raw_transcript_text="[00:05] BOT: Hello",
        structured_result={"order_placed": True},
    )
    assert saved["id"] == "test_res_1"

    history = list_saved_results()
    assert len(history) == 1
    assert history[0]["customer_name"] == "Lukas Test"


def test_location_geocoding_and_fixtures():
    sg_lat, _ = geocode_location("730123", "Singapore", "Singapore")
    assert abs(sg_lat - 1.3521) < 0.1
    assert any("Hawker" in r.name for r in get_offline_restaurants("Singapore"))

    lat, lon = geocode_location("12345", "Dorfstadt", "Deutschland")
    found = search_overpass_restaurants(lat, lon, dry_run=True, city="Dorfstadt")
    assert len(found) >= 5
    # Every candidate knows how far away it is; pickup ranking depends on it.
    assert all(r.distance_km is not None for r in found)


def test_offline_pool_is_copied_not_shared():
    """Annotating distances must not bleed from one visitor into the next."""
    first = search_overpass_restaurants(52.52, 13.405, dry_run=True, city="Dorfstadt")
    first[0].distance_km = 999.0
    second = get_offline_restaurants("Dorfstadt")
    assert second[0].distance_km != 999.0


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

def test_landing_offers_exactly_the_two_branches(client):
    page = client.get("/").text
    assert 'href="/order?lang=de"' in page
    assert 'href="/reserve?lang=de"' in page
    assert "Essen bestellen" in page
    assert "Tisch reservieren" in page
    # The user's sentence, and the hover explanation behind each tile.
    assert "wir finden, wer es dir liefert" in page
    assert "tile-hint" in page


def test_landing_carries_the_process_animation(client):
    page = client.get("/").text
    assert "<svg" in page and "cord-walk" in page
    assert "prefers-reduced-motion" in page
    # The three statements the animation makes, in text, for screen readers.
    assert "höflich verabschieden" in page
    assert "niemand mehr an" in page


def test_no_external_font_or_script_is_loaded(client):
    """The app claims to work offline. It has to mean it."""
    for path in ("/", "/order", "/reserve"):
        page = client.get(path).text
        assert "fonts.googleapis.com" not in page
        assert "fonts.gstatic.com" not in page
        assert "cdn." not in page


@pytest.mark.parametrize("path", ["/", "/order", "/reserve", "/history"])
def test_pages_render_in_both_languages(client, path):
    german = client.get(path + "?lang=de")
    english = client.get(path + "?lang=en")
    assert german.status_code == english.status_code == 200
    assert '<html lang="de"' in german.text
    assert '<html lang="en"' in english.text
    # No untranslated key names leaking through as visible text.
    for body in (german.text, english.text):
        assert "landing.claim" not in body
        assert "cascade.band" not in body


def test_language_choice_is_remembered(client):
    client.get("/?lang=en")
    later = client.get("/order")
    assert '<html lang="en"' in later.text


def test_food_branch_has_a_real_mode_switch(client):
    page = client.get("/order").text
    assert 'name="mode" value="delivery" checked' in page
    assert 'name="mode" value="pickup"' in page
    assert 'id="pickup-time-field" hidden' in page  # appears only on pickup
    assert 'id="maxdist-field" hidden' in page
    assert "HC.onModeChange()" in page


def test_table_branch_asks_its_own_questions(client):
    page = client.get("/reserve").text
    for field in ("reservation_date", "reservation_time", "party_size", "seating"):
        assert f'name="{field}"' in page
    # No money anywhere in the table branch.
    assert 'name="max_budget_eur"' not in page
    # The three concessions, each with its step number.
    for key in ("indoor_ok", "time_flex", "deposit_ok"):
        assert f'value="{key}"' in page


# --------------------------------------------------------------------------
# Candidates
# --------------------------------------------------------------------------

def search_form(**overrides):
    form = {
        "branch": "food",
        "mode": "delivery",
        "postcode": "12345",
        "city": "Dorfstadt",
        "radius_km": "3.0",
        "delivery_address": "Dorfstraße 10, 12345 Dorfstadt",
        "customer_name": "Lukas",
        "food_prompt": "Burger",
        "max_budget_eur": "35.00",
        "scenario": "jury_30s_demo",
    }
    form.update(overrides)
    return form


def test_search_ranks_candidates_and_publishes_the_order(client):
    page = client.post("/api/search", data=search_form()).text
    assert 'name="candidate_order"' in page
    order = page.split('id="candidate_order" value="')[1].split('"')[0].split(",")
    assert order[0] == "rest_burger_house"  # the craving beats the favourite
    assert "rest_trattoria_luigi" in order


def test_search_shows_why_a_candidate_was_skipped(client):
    """Skipped is not the same as hidden: the reason is on the page."""
    page = client.post("/api/search", data=search_form(mode="delivery")).text
    assert "Gasthaus Zur Linde" in page  # skipped: does not deliver
    assert "does not deliver" in page


def test_pickup_and_delivery_shortlist_different_places(client):
    """The switch reaches the candidate list, not just the wording.

    Delivery drops the village pub, which does not deliver at all. Pickup keeps
    it but honours a distance limit that delivery has no use for.
    """
    delivery_order = client.post("/api/search", data=search_form(
        food_prompt="Essen", mode="delivery")
    ).text.split('id="candidate_order" value="')[1].split('"')[0].split(",")

    pickup_near = client.post("/api/search", data=search_form(
        food_prompt="Essen", mode="pickup", pickup_time="19:00",
        max_distance_km="1.0", scenario="pickup_cascade")
    ).text.split('id="candidate_order" value="')[1].split('"')[0].split(",")

    pickup_far = client.post("/api/search", data=search_form(
        food_prompt="Essen", mode="pickup", pickup_time="19:00",
        max_distance_km="5.0", scenario="pickup_cascade")
    ).text.split('id="candidate_order" value="')[1].split('"')[0].split(",")

    assert "rest_gasthaus_linde" not in delivery_order   # does not deliver
    assert "rest_gasthaus_linde" in pickup_far           # but you can fetch it
    assert len(pickup_near) < len(pickup_far)            # the limit actually cuts


def test_table_search_filters_by_party_size(client):
    """A group of twelve is not a matter of negotiation for a four-seater."""
    form = {
        "branch": "table", "mode": "reservation", "postcode": "12345",
        "city": "Dorfstadt", "radius_km": "3.0",
        "delivery_address": "Dorfstraße 10", "customer_name": "Lukas",
        "food_prompt": "Italienisch", "reservation_date": "2026-08-07",
        "reservation_time": "19:00", "party_size": "12", "seating": "any",
        "scenario": "table_cascade",
    }
    page = client.post("/api/search", data=form).text
    order = page.split('id="candidate_order" value="')[1].split('"')[0].split(",")
    assert order == ["rest_gasthaus_linde"]  # the only house that seats twelve
    assert "seats at most" in page


# --------------------------------------------------------------------------
# The goal text
# --------------------------------------------------------------------------

def test_goal_preview_comes_from_the_engine_not_from_javascript(client):
    form = search_form()
    form["candidate_order"] = "rest_burger_house"
    data = client.post("/api/preview-goal", data=form).json()

    assert "automated assistant calling on behalf of Lukas" in data["goal"]
    assert "35.00 EUR" in data["goal"]
    assert "Do you deliver to this address?" in data["goal"]


def test_goal_preview_follows_the_mode(client):
    delivery = client.post("/api/preview-goal", data=search_form(
        candidate_order="rest_burger_house")).json()["goal"]
    pickup = client.post("/api/preview-goal", data=search_form(
        mode="pickup", pickup_time="19:30",
        candidate_order="rest_burger_house")).json()["goal"]

    assert "delivery fee" in delivery
    assert "no delivery fee, we collect ourselves" in pickup
    assert "pickup order" in pickup.lower()


def test_goal_preview_carries_concessions_in_order(client):
    form = {
        "branch": "table", "mode": "reservation", "city": "Dorfstadt",
        "customer_name": "Lukas", "food_prompt": "Italienisch",
        "reservation_date": "2026-08-07", "reservation_time": "19:00",
        "party_size": "4", "seating": "outdoor",
        "candidate_order": "rest_trattoria_luigi",
        "concessions": ["deposit_ok", "indoor_ok"],
    }
    goal = client.post("/api/preview-goal", data=form).json()["goal"]

    # Granted out of order, handed over in tier order.
    assert goal.index("indoor table is acceptable") < goal.index("booking deposit")
    assert "Never offer a later step before an earlier one has failed" in goal


def test_goal_preview_refuses_prohibited_content(client):
    form = search_form(food_prompt="call the hospital for me")
    response = client.post("/api/preview-goal", data=form)
    assert response.status_code == 400
    assert "Sprachagent" in response.json()["error"]


# --------------------------------------------------------------------------
# The cascade
# --------------------------------------------------------------------------

def cascade_form(**overrides):
    form = search_form()
    form.update({
        "candidate_order": "rest_burger_house,rest_trattoria_luigi,rest_asian_wok",
        "selected_restaurants": ["rest_burger_house", "rest_trattoria_luigi", "rest_asian_wok"],
    })
    form.update(overrides)
    return form


def test_cascade_rejects_then_succeeds_and_stops(client):
    events, _ = run_cascade(client, cascade_form())
    kinds = [e["type"] for e in events]

    assert kinds.count("rejected") == 2
    assert kinds.count("accepted") == 1
    assert kinds[-1] == "done"

    rejections = [e for e in events if e["type"] == "rejected"]
    assert "exceeds maximum budget limit" in rejections[0]["reason"]
    assert "Unclear price" in rejections[1]["reason"]

    accepted = next(e for e in events if e["type"] == "accepted")
    assert accepted["id"] == "rest_asian_wok"
    # Nobody after the success gets dialled.
    dialed = [e["id"] for e in events if e["type"] == "dialing"]
    assert dialed == ["rest_burger_house", "rest_trattoria_luigi", "rest_asian_wok"]


def test_cascade_calls_in_the_order_the_user_arranged(client):
    """The arrows moved DOM nodes before; now they move the actual call order."""
    reordered = cascade_form(
        candidate_order="rest_asian_wok,rest_burger_house,rest_trattoria_luigi")
    events, _ = run_cascade(client, reordered)

    dialed = [e["id"] for e in events if e["type"] == "dialing"]
    assert dialed == ["rest_asian_wok"]  # succeeds first, so nobody else is called
    assert [e["type"] for e in events].count("accepted") == 1


def test_unselected_candidates_are_never_called(client):
    form = cascade_form(selected_restaurants=["rest_asian_wok"])
    events, _ = run_cascade(client, form)
    dialed = [e["id"] for e in events if e["type"] == "dialing"]
    assert dialed == ["rest_asian_wok"]


def test_cascade_streams_the_conversation_while_it_happens(client):
    events, _ = run_cascade(client, cascade_form())
    activity = [e for e in events if e["type"] == "activity"]
    assert len(activity) > 5
    assert any("Callee said" in e["line"] for e in activity)
    # Activity for a candidate arrives before that candidate's verdict.
    first_verdict = next(i for i, e in enumerate(events) if e["type"] == "rejected")
    assert any(e["type"] == "activity" for e in events[:first_verdict])


def test_result_card_reports_calls_actually_made(client):
    events, _ = run_cascade(client, cascade_form())
    outcome = next(e for e in events if e["type"] == "outcome")
    assert "3 Anrufe geführt" in outcome["html"]
    assert "Asia Wok Express" in outcome["html"]


def test_single_call_is_counted_in_the_singular(client):
    """'1 Anrufe geführt' is the kind of detail that makes a page feel machine-made."""
    events, _ = run_cascade(client, cascade_form(
        candidate_order="rest_asian_wok", selected_restaurants=["rest_asian_wok"]))
    outcome = next(e for e in events if e["type"] == "outcome")
    assert "1 Anruf geführt" in outcome["html"]
    assert "1 Anrufe" not in outcome["html"]


def test_result_sentence_follows_the_interface_language(client):
    """The one sentence a person reads out loud has to be in their language."""
    german = next(e for e in run_cascade(client, cascade_form())[0]
                  if e["type"] == "outcome")["html"]
    assert "Bestellt bei Asia Wok Express" in german
    assert "Rückruf unter" in german
    assert "Ordered from" not in german

    client.get("/?lang=en")
    english = next(e for e in run_cascade(client, cascade_form())[0]
                   if e["type"] == "outcome")["html"]
    assert "Ordered from Asia Wok Express" in english
    assert "Callback at" in english


def test_cancel_stops_the_cascade(client):
    started = client.post("/api/start-cascade", data=cascade_form())
    order_id = started.text.split('HC.startStream("')[1].split('"')[0]

    cancel = client.post("/api/cancel-cascade", data={"order_id": order_id})
    assert cancel.status_code == 200  # used to be a 422: order_id went as a query param

    events = sse_events(client.get(f"/api/cascade-stream?order_id={order_id}").text)
    assert events[-1]["type"] == "canceled"
    assert not [e for e in events if e["type"] == "accepted"]
    web.CANCELED_ORDERS.discard(order_id)


def test_exhausted_cascade_says_so_plainly(client):
    """Only the two candidates that decline — no success to fall back on."""
    form = cascade_form(
        candidate_order="rest_burger_house,rest_trattoria_luigi",
        selected_restaurants=["rest_burger_house", "rest_trattoria_luigi"])
    events, _ = run_cascade(client, form)

    outcome = next(e for e in events if e["type"] == "outcome")
    assert "Keiner hat die Bedingungen erfüllt" in outcome["html"]
    assert not [e for e in events if e["type"] == "accepted"]


def test_table_cascade_books_a_table_and_names_the_seating(client):
    form = {
        "branch": "table", "mode": "reservation", "city": "Dorfstadt",
        "postcode": "12345", "radius_km": "3.0",
        "delivery_address": "Dorfstraße 10", "customer_name": "Lukas",
        "food_prompt": "Italienisch", "reservation_date": "2026-08-07",
        "reservation_time": "19:00", "party_size": "4", "seating": "outdoor",
        "scenario": "table_cascade",
        "candidate_order": "rest_trattoria_luigi,rest_gasthaus_linde",
        "selected_restaurants": ["rest_trattoria_luigi", "rest_gasthaus_linde"],
    }
    events, _ = run_cascade(client, form)

    rejected = [e for e in events if e["type"] == "rejected"]
    assert rejected and "Fully booked" in rejected[0]["reason"]

    outcome = next(e for e in events if e["type"] == "outcome")
    assert "Gasthaus Zur Linde" in outcome["html"]
    assert "Draußen" in outcome["html"]
    assert "€" not in outcome["html"]  # no money in the table branch


def test_table_cascade_refuses_a_concession_that_was_not_granted(client):
    base = {
        "branch": "table", "mode": "reservation", "city": "Dorfstadt",
        "postcode": "12345", "radius_km": "3.0",
        "delivery_address": "Dorfstraße 10", "customer_name": "Lukas",
        "food_prompt": "Italienisch", "reservation_date": "2026-08-07",
        "reservation_time": "19:00", "party_size": "4", "seating": "outdoor",
        "scenario": "table_concession_cascade",
        "candidate_order": "rest_trattoria_luigi,rest_gasthaus_linde",
        "selected_restaurants": ["rest_trattoria_luigi", "rest_gasthaus_linde"],
    }

    without, _ = run_cascade(client, dict(base))
    assert not [e for e in without if e["type"] == "accepted"]
    reasons = " ".join(e["reason"] for e in without if e["type"] == "rejected")
    assert "not authorised" in reasons

    granted = dict(base)
    granted["concessions"] = ["indoor_ok"]
    with_grant, _ = run_cascade(client, granted)
    accepted = [e for e in with_grant if e["type"] == "accepted"]
    assert accepted and accepted[0]["id"] == "rest_gasthaus_linde"

    outcome = next(e for e in with_grant if e["type"] == "outcome")
    assert "Zugeständnis eingelöst" in outcome["html"]


# --------------------------------------------------------------------------
# Saving and history
# --------------------------------------------------------------------------

def test_saved_result_keeps_the_mode_that_actually_happened(client):
    """A booked table used to be filed as a food order: mode was hardcoded."""
    form = {
        "branch": "table", "mode": "reservation", "city": "Dorfstadt",
        "postcode": "12345", "radius_km": "3.0",
        "delivery_address": "Dorfstraße 10", "customer_name": "Lukas",
        "food_prompt": "Italienisch", "reservation_date": "2026-08-07",
        "reservation_time": "19:00", "party_size": "4", "seating": "any",
        "scenario": "table_cascade",
        "candidate_order": "rest_gasthaus_linde",
        "selected_restaurants": ["rest_gasthaus_linde"],
    }
    _, order_id = run_cascade(client, form)

    saved = client.post("/api/save-result", data={
        "order_id": order_id, "restaurant_id": "rest_gasthaus_linde"})
    assert saved.status_code == 200

    rows = client.get("/api/saved-results").json()
    assert rows[0]["mode"] == "reservation"
    assert rows[0]["restaurant_name"] == "Gasthaus Zur Linde"
    # Masking is done by mask_phone, not by slicing the string.
    assert "..." not in rows[0]["masked_phone"]
    assert "•" in rows[0]["masked_phone"]


def test_history_page_lists_saved_results(client):
    form = cascade_form()
    _, order_id = run_cascade(client, form)
    client.post("/api/save-result", data={"order_id": order_id})

    page = client.get("/history").text
    assert "Asia Wok Express" in page
    assert "Gesicherte Ergebnisse" in page


def test_saving_without_a_finished_run_does_not_invent_one(client):
    response = client.post("/api/save-result", data={"order_id": "ord_nothing"})
    assert response.status_code == 200
    assert client.get("/api/saved-results").json() == []


# --------------------------------------------------------------------------
# Escaping
# --------------------------------------------------------------------------

def test_user_text_is_escaped_before_it_reaches_the_page(client):
    nasty = '<img src=x onerror="alert(1)">'
    page = client.post("/api/search", data=search_form(food_prompt=nasty)).text
    assert "<img src=x" not in page

    goal = client.post("/api/preview-goal", data=search_form(
        food_prompt=nasty, candidate_order="rest_burger_house")).json()
    # JSON transport is fine; what matters is that no raw tag lands in HTML.
    assert nasty in goal["goal"]
