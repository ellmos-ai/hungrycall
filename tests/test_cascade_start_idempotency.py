"""Regression coverage for E23 (Nutzer-Befund Endabnahme, 2026-08-22).

A fast double-click on "Start calls" fired three POSTs to
/api/start-cascade; each one minted its own order_id and its own
HC.startStream(order_id) script, and the risk was not just a flickering
display but a second, invisible cascade dialling real restaurants a second
time with no monitor showing it. Three guards close that: the Start button
locks itself while its request is in flight (hx-disabled-elt), a duplicate
/api/start-cascade for a session that already has a cascade running hands
back that SAME order instead of minting a new one, and a given order_id's
/api/cascade-stream is only ever allowed to actually dial once. An OSM
outage answering 200 like a normal search -- indistinguishable from success
at the HTTP level -- was part of what let the race go unnoticed, so that
gets its own status code too.
"""

import json
import os

import pytest
from fastapi.testclient import TestClient

from hungrycall import web
from hungrycall.db import init_db
from hungrycall.location import SearchServiceUnavailable
from hungrycall.models import CallResult, CallStatus
from hungrycall.web import app


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_file = str(tmp_path / "test_hungrycall.db")
    os.environ["HUNGRYCALL_DB_PATH"] = db_file
    init_db(db_file)
    yield db_file
    os.environ.pop("HUNGRYCALL_DB_PATH", None)


@pytest.fixture(autouse=True)
def instant_cascade(monkeypatch):
    """Drop the simulated dialling delays so these tests finish quickly."""
    monkeypatch.setattr(web, "DRY_RUN_DIAL_SECONDS", 0)
    monkeypatch.setattr(web, "DRY_RUN_TURN_SECONDS", 0)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
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


def cascade_form(**overrides):
    form = search_form()
    form.update({
        "candidate_order": "rest_burger_house,rest_trattoria_luigi,rest_asian_wok",
        "selected_restaurants": ["rest_burger_house", "rest_trattoria_luigi", "rest_asian_wok"],
    })
    form.update(overrides)
    return form


def order_id_of(response) -> str:
    return response.text.split('HC.startStream("')[1].split('"')[0]


def sse_events(text):
    return [
        json.loads(line[len("data: "):])
        for line in text.splitlines()
        if line.startswith("data: ")
    ]


def test_a_duplicate_start_post_for_the_same_session_reuses_the_running_order(client):
    """The Start-Button-Race scenario: two POSTs before either stream opens."""
    orders_before = set(web.ACTIVE_ORDERS)

    first = client.post("/api/start-cascade", data=cascade_form())
    second = client.post("/api/start-cascade", data=cascade_form())

    assert first.status_code == 200
    assert second.status_code == 200
    assert order_id_of(first) == order_id_of(second)
    # Exactly one NEW order was created by these two POSTs together, not two.
    assert set(web.ACTIVE_ORDERS) - orders_before == {order_id_of(first)}


def test_a_second_stream_request_for_the_same_order_does_not_dial_again(client):
    """Even if a second EventSource reaches the same order_id -- e.g. the
    browser's native auto-reconnect, or a second HC.startStream() call from
    the duplicate response above -- the candidates must not be dialled a
    second time."""
    started = client.post("/api/start-cascade", data=cascade_form())
    order_id = order_id_of(started)

    calls = {"n": 0}

    class CountingClient:
        def execute_candidate_call(self, restaurant, user_request, idempotency_key):
            calls["n"] += 1
            return CallResult(
                call_id=f"call_{calls['n']}",
                run_id="run_1",
                status=CallStatus.COMPLETED,
                task_completed=True,
                completion_confidence=1.0,
                structured_result={
                    "delivers_to_address": True,
                    "price_known": True,
                    "total_price_eur": 10.0,
                    "order_placed": True,
                    "eta_minutes": 20,
                },
                transcript=[],
                post_summary="ok",
                activity=[],
            )

    web.ACTIVE_ORDERS[order_id]["call_client"] = CountingClient()

    first_stream = client.get(f"/api/cascade-stream?order_id={order_id}")
    assert calls["n"] == 1
    first_events = sse_events(first_stream.text)
    assert any(e["type"] == "accepted" for e in first_events)

    second_stream = client.get(f"/api/cascade-stream?order_id={order_id}")
    # No further call was placed -- the second stream refused to dial again.
    assert calls["n"] == 1
    second_events = sse_events(second_stream.text)
    assert not any(e["type"] == "dialing" for e in second_events)
    assert not any(e["type"] == "accepted" for e in second_events)


def test_a_finished_cascade_releases_the_session_lock_for_a_new_start(client):
    """Once a cascade actually finishes, the same session can start a
    genuinely new one -- the lock is not permanent."""
    first_started = client.post("/api/start-cascade", data=cascade_form())
    first_order_id = order_id_of(first_started)
    client.get(f"/api/cascade-stream?order_id={first_order_id}")  # drain to "done"

    second_started = client.post("/api/start-cascade", data=cascade_form(
        candidate_order="rest_asian_wok",
        selected_restaurants=["rest_asian_wok"],
    ))
    second_order_id = order_id_of(second_started)

    assert second_order_id != first_order_id
    assert second_order_id in web.ACTIVE_ORDERS


def test_an_osm_outage_at_start_gets_its_own_status_code(client, monkeypatch):
    """503, not the 200 an ordinary search-with-an-error-panel gets -- an
    OSM failure answering 200 was part of what made the race invisible."""
    def unavailable(*args, **kwargs):
        raise SearchServiceUnavailable("Overpass returned HTTP 503")

    monkeypatch.setattr(web, "geocode_location", unavailable)

    response = client.post("/api/start-cascade", data=cascade_form())

    assert response.status_code == 503
    assert "HC.startStream(" not in response.text


def test_the_start_button_disables_itself_for_the_duration_of_its_own_request(client):
    page = client.post("/api/search?lang=en", data=search_form()).text
    assert 'hx-disabled-elt="this"' in page
