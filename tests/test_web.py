"""Tests for the web interface, DB layer and location lookup.

The emphasis is on the things that used to only look like they worked: the
candidate order, the goal preview, the cancel button, the mode switch and the
saved result's mode.
"""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hungrycall import web
from hungrycall.call_client import DryRunCallClient
from hungrycall.db import (
    create_order_record,
    init_db,
    list_saved_results,
    save_cascade_result,
)
from hungrycall.location import (
    geocode_location,
    get_offline_restaurants,
    search_overpass_restaurants,
)
from hungrycall.models import CallResult, CallStatus
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
    test_client = TestClient(app)
    response = test_client.post(
        "/restaurant-test-mode/toggle?lang=en&next=%2Forder",
        follow_redirects=False,
    )
    assert response.status_code == 303
    return test_client


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
        customer_name="Alex Beispiel",
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
        callback_number="+441632960000",
        total_price_eur=28.50,
        eta_minutes=35,
        post_summary="Order confirmed successfully",
        raw_transcript_text="[00:05] BOT: Hello",
        structured_result={"order_placed": True},
    )
    assert saved["id"] == "test_res_1"

    history = list_saved_results()
    assert len(history) == 1
    assert history[0]["customer_name"] == "Alex Beispiel"


def test_location_geocoding_and_fixtures():
    sg_lat, _ = geocode_location("730123", "Singapore", "Singapore", test_mode=True)
    assert abs(sg_lat - 1.3521) < 0.1
    assert any("Hawker" in r.name for r in get_offline_restaurants("Singapore"))

    lat, lon = geocode_location("12345", "Dorfstadt", "Deutschland", test_mode=True)
    found = search_overpass_restaurants(lat, lon, test_mode=True, city="Dorfstadt")
    assert len(found) >= 5
    # Every candidate knows how far away it is; pickup ranking depends on it.
    assert all(r.distance_km is not None for r in found)


def test_offline_pool_is_copied_not_shared():
    """Annotating distances must not bleed from one visitor into the next."""
    first = search_overpass_restaurants(52.52, 13.405, test_mode=True, city="Dorfstadt")
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


def test_approved_brand_assets_are_packaged_and_served(client):
    repo_root = Path(__file__).resolve().parents[1]
    brand_dir = repo_root / "hungrycall" / "static" / "brand"
    expected_sizes = {
        "motiv.png": (1024, 1024),
        "motiv-aus.png": (1024, 1024),
        "motiv-an.png": (1024, 1024),
        "thumbnail.png": (1280, 720),
        "logo-square.png": (512, 512),
    }

    for name, dimensions in expected_sizes.items():
        payload = (brand_dir / name).read_bytes()
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        assert (int.from_bytes(payload[16:20], "big"),
                int.from_bytes(payload[20:24], "big")) == dimensions
        response = client.get(f"/static/brand/{name}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    banner = (repo_root / "banner.png").read_bytes()
    assert (int.from_bytes(banner[16:20], "big"),
            int.from_bytes(banner[20:24], "big")) == (1200, 300)
    for readme in ("README.md", "README_de.md"):
        first_line = (repo_root / readme).read_text(encoding="utf-8").splitlines()[0]
        assert first_line == "![I am hungry](banner.png)"


def test_landing_uses_one_shot_accessible_fridge_reveal(client):
    german = client.get("/?lang=de").text
    english = client.get("/?lang=en").text

    assert 'class="brand-mark" src="/static/brand/motiv.png"' in german
    assert '<link rel="icon" type="image/png" href="/static/brand/logo-square.png">' in german
    assert '/static/brand/motiv-aus.png' in german
    assert '/static/brand/motiv-an.png' in german
    assert german.index("fridge-layer-off") < german.index("fridge-layer-on")
    assert "Der Kühlschrank ist leer" in german
    assert "The fridge is empty" in english
    assert "Ein leerer Kühlschrank im Dunkeln" in german
    assert "An empty fridge in the dark" in english

    light_rule = german.split(".fridge-layer-on {", 1)[1].split("}", 1)[0]
    assert "fridge-light-on" in light_rule
    assert "forwards" in light_rule
    assert "infinite" not in light_rule
    assert ".fridge-layer-off { opacity: 0; animation: none !important; }" in german
    assert ".fridge-layer-on { opacity: 1; animation: none !important; }" in german


def test_no_external_font_or_script_is_loaded(client):
    """The app claims to work offline. It has to mean it."""
    for path in ("/", "/order", "/reserve"):
        page = client.get(path).text
        assert "fonts.googleapis.com" not in page
        assert "fonts.gstatic.com" not in page
        assert "cdn." not in page


def test_light_theme_is_default_and_dark_is_an_explicit_saved_mode(client):
    page = client.get("/").text
    script = client.get("/static/app.js").text
    assert "--ink:          #F7F9FF" in page
    assert 'html[data-theme="dark"]' in page
    assert '<html lang="de">' in page
    assert 'id="theme-toggle"' in page
    assert 'localStorage.getItem("hc-theme")' in page
    assert 'localStorage.setItem("hc-theme"' in script
    for color in ("#2563EB", "#7C3AED", "#EC4899", "#82F21B"):
        assert color in page


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


def test_live_transport_is_an_explicit_opt_in_while_simulation_is_the_default(client):
    with TestClient(app) as plain_client:
        page = plain_client.get("/order?lang=de").text
        assert 'id="transport-default" name="transport" value="dry_run"' in page
        assert 'id="transport-live" name="transport" value="live"' in page
        assert "Echte Anrufe — kostet Geld" in page
        assert 'id="confirm-live"' in page
        assert 'id="live-confirm-panel" hidden' in page
        assert "Trockenlauf-Szenario" not in page


def test_scenario_picker_only_appears_with_the_explicit_test_mode(client):
    active_page = client.get("/order?lang=de").text
    assert 'id="scenario" name="scenario"' in active_page
    assert 'id="transport-live"' not in active_page

    with TestClient(app) as plain_client:
        off = plain_client.get("/order?lang=de").text
        assert 'id="scenario"' not in off

        toggled = plain_client.post(
            "/restaurant-test-mode/toggle?lang=de&next=%2Forder",
            follow_redirects=True,
        )
        assert toggled.status_code == 200
        assert 'id="scenario" name="scenario"' in toggled.text
        assert "Test-Szenario" in toggled.text


def test_live_transport_needs_the_second_confirmation(client):
    response = client.post(
        "/api/search?lang=de", data=search_form(transport="live")
    )
    assert response.status_code == 400
    assert "nicht ausdrücklich bestätigt" in response.text


def test_confirmed_live_transport_reaches_the_real_client_seam(client, monkeypatch):
    # Live calls and restaurant fixtures cannot be combined. Leave the fixture
    # workspace before exercising the real-client seam.
    client.post(
        "/restaurant-test-mode/toggle?lang=de&next=%2Forder",
        follow_redirects=False,
    )
    # The seam is web.live_call_client(): one function decides whose key pays
    # for a live call, so this is where a test stands in for the real client.
    monkeypatch.setattr(web, "live_call_client", lambda: DryRunCallClient("jury_30s_demo"))
    pool = search_overpass_restaurants(
        52.52, 13.405, test_mode=True, city="Dorfstadt"
    )
    monkeypatch.setattr(web, "geocode_location", lambda *args, **kwargs: (52.52, 13.405))
    monkeypatch.setattr(web, "rebuild_pool", lambda *args, **kwargs: pool)
    form = cascade_form(transport="live", confirm_live="yes", test_mode="")
    started = client.post("/api/start-cascade?lang=de", data=form)
    assert started.status_code == 200
    assert "Echte Anrufe — kostet Geld" in started.text
    order_id = started.text.split('HC.startStream("')[1].split('"')[0]
    assert web.ACTIVE_ORDERS[order_id]["live_mode"] is True
    assert isinstance(web.ACTIVE_ORDERS[order_id]["call_client"], DryRunCallClient)


def test_web_stream_redacts_an_echoed_requester_callback_before_sse_and_save(
    client, setup_test_db
):
    callback = "+441632960090"

    class EchoingClient:
        def execute_candidate_call(self, restaurant, user_request, idempotency_key):
            return CallResult(
                call_id="echo-call",
                run_id="echo-run",
                status=CallStatus.COMPLETED,
                task_completed=True,
                completion_confidence=1.0,
                structured_result={
                    "delivers_to_address": True,
                    "price_known": True,
                    "total_price_eur": 20,
                    "eta_minutes": 25,
                    "order_placed": True,
                    "callback_number": restaurant.phone,
                    "debug_echo": callback,
                    "rejection_reason": f"echo {callback}",
                },
                transcript=[{"text": f"human {callback}"}],
                post_summary=f"restaurant repeated {callback}",
                rejection_reason=f"echoed {callback}",
                activity=[f"Callee repeated {callback}"],
                raw_transcript_text=f"human {callback}",
            )

    started = client.post("/api/start-cascade", data=cascade_form())
    order_id = started.text.split('HC.startStream("')[1].split('"')[0]
    web.ACTIVE_ORDERS[order_id]["call_client"] = EchoingClient()
    stream = client.get(f"/api/cascade-stream?order_id={order_id}")
    assert callback not in stream.text

    saved = client.post("/api/save-result", data={"order_id": order_id})
    assert saved.status_code == 200
    assert callback not in json.dumps(list_saved_results())
    assert callback.encode("utf-8") not in Path(setup_test_db).read_bytes()


def test_table_branch_asks_its_own_questions(client):
    page = client.get("/reserve?lang=en").text
    for field in ("reservation_date", "reservation_time", "party_size", "seating"):
        assert f'name="{field}"' in page
    assert 'name="max_budget_eur"' not in page
    for field in (
        "first_name", "last_name", "requester_callback_number", "seating_custom",
        "special_instructions", "earlier_hours", "later_hours", "earlier_minutes",
        "later_minutes", "max_booking_fee_eur",
    ):
        assert f'name="{field}"' in page
    assert 'value="custom"' in page
    assert 'id="earlier_hours" name="earlier_hours"' in page
    assert 'id="later_hours" name="later_hours"' in page
    assert 'id="earlier_minutes" name="earlier_minutes" value="0" min="0" max="59"' in page
    assert 'id="later_minutes" name="later_minutes" value="0" min="0" max="59"' in page
    assert 'id="seating-custom-field" hidden' in page
    assert 'id="seating_custom" name="seating_custom"' in page
    assert 'placeholder="Our usual table under the palm tree, please — thank you." disabled' in page
    assert 'onchange="HC.onSeatingChange()"' in page


def test_history_rerun_splits_the_legacy_combined_name(client):
    create_order_record(
        order_id="name-split-order",
        mode="delivery",
        customer_name="Ada Lovelace",
        food_prompt="Pizza",
        max_budget_eur=25,
        delivery_address="Example Street 1",
    )
    page = client.get("/order?lang=en&history=name-split-order").text
    assert 'id="first_name" name="first_name" value="Ada"' in page
    assert 'id="last_name" name="last_name" value="Lovelace"' in page
    assert 'id="requester_callback_number" name="requester_callback_number" value=""' in page


def test_food_order_starts_with_an_editable_position_and_separate_templates(client):
    page = client.get("/order?lang=en").text
    assert 'id="order-chain-builder"' in page
    assert 'id="add-order-position"' in page
    assert "Order wish chains" in page
    assert "Templates" in page
    assert "Name and callback" in page
    assert "Price range" in page
    for field in ("first_name", "last_name", "requester_callback_number"):
        assert f'name="{field}"' in page


def test_order_chain_seed_script_creates_hc_before_assigning_to_it(client):
    # app.js is deferred, so every inline script runs before it. The seed
    # script that carries orderChainInitial must therefore create window.HC
    # itself: without the guard the assignment throws a ReferenceError, the
    # seed never lands and the whole chain editor sits inert -- found live
    # in the 2026-08-22 final-acceptance GUI run.
    page = client.get("/order?lang=en").text
    seed = page.index("HC.orderChainInitial")
    guard = page.rindex("window.HC = window.HC || {};", 0, seed)
    # The guard must sit inside the same script block as the assignment,
    # not in some earlier or later block.
    script_open = page.rindex("<script>", 0, seed)
    assert script_open < guard < seed


def test_landing_places_the_fridge_left_of_the_claim_on_desktop_and_stacks_on_mobile(client):
    page = client.get("/?lang=en").text
    assert ".fridge-reveal {\n  /* The product comes first on desktop: fridge left, the invitation right. */\n  order: -1;" in page
    assert ".fridge-reveal { order: 0; width: min(100%, 32rem); justify-self: center; }" in page


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
        "first_name": "Alex",
        "last_name": "Test",
        "requester_callback_number": "+441632960090",
        "food_prompt": "Burger",
        "max_budget_eur": "35.00",
        "scenario": "jury_30s_demo",
    }
    form.update(overrides)
    return form


def test_search_requires_a_name_and_callback_number(client):
    without_name = search_form()
    without_name.pop("first_name")
    response = client.post("/api/search", data=without_name)
    assert response.status_code == 400
    assert "first_name is required" in response.text

    without_callback = search_form()
    without_callback.pop("requester_callback_number")
    response = client.post("/api/search", data=without_callback)
    assert response.status_code == 400
    assert "requester_callback_number" in response.text


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
        "delivery_address": "Dorfstraße 10", "first_name": "Alex", "last_name": "Test",
        "requester_callback_number": "+441632960090",
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

    assert "automatisierter Assistent im Auftrag von Alex" in data["goal"]
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


def test_goal_preview_ignores_removed_legacy_concessions(client):
    form = {
        "branch": "table", "mode": "reservation", "city": "Dorfstadt",
        "first_name": "Alex", "last_name": "Test", "requester_callback_number": "+441632960090",
        "food_prompt": "Italienisch",
        "reservation_date": "2026-08-07", "reservation_time": "19:00",
        "party_size": "4", "seating": "outdoor",
        "candidate_order": "rest_trattoria_luigi",
        # Real, currently-valid FOOD_CONCESSIONS keys — proves reservation mode
        # discards concessions even when the key exists and would apply to a
        # food order, not just when the key happens to be unknown.
        "concessions": ["higher_price_ok", "wait_longer_ok"],
    }
    goal = client.post("/api/preview-goal", data=form).json()["goal"]

    assert "up to 3 EUR more than the maximum budget" not in goal
    assert "waiting up to 15 minutes longer" not in goal
    assert "Do not accept any booking fee or deposit" in goal


def test_food_concession_checkboxes_reach_the_goal_in_tier_order(client):
    """Coverage-map finding #12: the concession ladder must be reachable.

    Submitted out of tier order (substitute_ok is tier 3, wait_longer_ok is
    tier 1) — the goal must still list Step 1 before Step 2, proving the
    server does the ordering rather than trusting form order.
    """
    delivery = client.post("/api/preview-goal", data=search_form(
        candidate_order="rest_burger_house",
        concessions=["substitute_ok", "wait_longer_ok"],
    )).json()["goal"]

    assert "Step 1: only if the previous attempt failed, waiting up to 15 minutes longer" in delivery
    assert "Step 2: only if the previous attempt failed, accepting a similar substitute" in delivery
    assert delivery.index("Step 1:") < delivery.index("Step 2:")
    # The third, unauthorised concession must not appear at all.
    assert "3 EUR more than the maximum budget" not in delivery

    pickup = client.post("/api/preview-goal", data=search_form(
        mode="pickup", pickup_time="19:30",
        candidate_order="rest_burger_house",
        concessions=["higher_price_ok"],
    )).json()["goal"]
    assert "paying up to 3 EUR more than the maximum budget stated above is acceptable" in pickup


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


def test_cascade_cannot_restore_a_candidate_filtered_from_delivery(client):
    """A modified POST must not revive a restaurant that does not deliver.

    The search screen reports Gasthaus Zur Linde as skipped for delivery.  The
    cascade endpoint rebuilds its pool, so it must apply the same eligibility
    rule before accepting browser-supplied ids; otherwise a crafted form can
    dial a place that the visible product explicitly ruled out.
    """
    started = client.post("/api/start-cascade", data=cascade_form(
        candidate_order="rest_gasthaus_linde",
        selected_restaurants=["rest_gasthaus_linde"],
    ))

    assert started.status_code == 200
    assert "HC.startStream(" not in started.text
    assert "Kein Kandidat erfüllt die Vorbedingungen" in started.text


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
        "delivery_address": "Dorfstraße 10", "first_name": "Alex", "last_name": "Test",
        "requester_callback_number": "+441632960090",
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
    assert "0.00 €" in outcome["html"]  # explicit: no booking fee was spent


def test_table_cascade_cannot_be_reopened_by_a_legacy_concession(client):
    base = {
        "branch": "table", "mode": "reservation", "city": "Dorfstadt",
        "postcode": "12345", "radius_km": "3.0",
        "delivery_address": "Dorfstraße 10", "first_name": "Alex", "last_name": "Test",
        "requester_callback_number": "+441632960090",
        "food_prompt": "Italienisch", "reservation_date": "2026-08-07",
        "reservation_time": "19:00", "party_size": "4", "seating": "outdoor",
        "scenario": "table_concession_cascade",
        "candidate_order": "rest_trattoria_luigi,rest_gasthaus_linde",
        "selected_restaurants": ["rest_trattoria_luigi", "rest_gasthaus_linde"],
    }

    without, _ = run_cascade(client, dict(base))
    assert not [e for e in without if e["type"] == "accepted"]
    reasons = " ".join(e["reason"] for e in without if e["type"] == "rejected")
    assert "outdoor was requested" in reasons

    granted = dict(base)
    granted["concessions"] = ["wait_longer_ok"]  # a real, currently-valid FOOD_CONCESSIONS key
    with_grant, _ = run_cascade(client, granted)
    assert not [e for e in with_grant if e["type"] == "accepted"]


# --------------------------------------------------------------------------
# Saving and history
# --------------------------------------------------------------------------

def test_saved_result_keeps_the_mode_that_actually_happened(client):
    """A booked table used to be filed as a food order: mode was hardcoded."""
    form = {
        "branch": "table", "mode": "reservation", "city": "Dorfstadt",
        "postcode": "12345", "radius_km": "3.0",
        "delivery_address": "Dorfstraße 10", "first_name": "Alex", "last_name": "Test",
        "requester_callback_number": "+441632960090",
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


def test_live_with_fixtures_stays_refused_without_field_trial(client, monkeypatch):
    """Fixture phones belong to strangers; without the override the combination
    of restaurant test mode and a live wire must keep failing closed."""
    monkeypatch.delenv("HUNGRYCALL_FIELD_TRIAL_PHONE", raising=False)
    form = cascade_form(transport="live", confirm_live="yes")
    response = client.post("/api/start-cascade?lang=en", data=form)
    assert response.status_code == 400
    assert "must not be used for real calls" in response.text


def test_live_with_fixtures_allowed_under_field_trial_override(client, monkeypatch):
    """With the consenting test number configured, a supervised field trial may
    run live against fixture restaurants — every candidate is rewired to it."""
    trial_number = "+4910004069001"
    monkeypatch.setenv("HUNGRYCALL_FIELD_TRIAL_PHONE", trial_number)
    monkeypatch.setattr(web, "live_call_client", lambda: DryRunCallClient("jury_30s_demo"))
    form = cascade_form(transport="live", confirm_live="yes")
    started = client.post("/api/start-cascade?lang=en", data=form)
    assert started.status_code == 200
    order_id = started.text.split('HC.startStream("')[1].split('"')[0]
    order = web.ACTIVE_ORDERS[order_id]
    assert order["live_mode"] is True
    assert order["field_trial_number"] == trial_number
    assert all(r.phone == trial_number for r in order["candidates"])


def test_every_dialled_attempt_is_persisted_with_its_transcript(client):
    """The successful attempt is the customer's order receipt, the rejected
    ones explain the cascade — both must survive the stream (user decision
    2026-08-11: 'Bestellnachweis, also speichern sollte schon immer sein')."""
    from hungrycall.db import list_call_attempts

    events, order_id = run_cascade(client, cascade_form())
    attempts = list_call_attempts(order_id)
    kinds = [e["type"] for e in events]
    dialled = kinds.count("rejected") + kinds.count("accepted")
    assert len(attempts) == dialled and dialled >= 3
    accepted = [a for a in attempts if a["passed"]]
    rejected = [a for a in attempts if not a["passed"]]
    assert len(accepted) == 1 and len(rejected) == dialled - 1
    assert all(a["run_id"] for a in attempts)
    assert accepted[0]["transcript"]
    assert all(a["rejection_reason"] for a in rejected)
    fetched = client.get(f"/api/order-attempts?order_id={order_id}").json()
    assert [a["id"] for a in fetched] == [a["id"] for a in attempts]
