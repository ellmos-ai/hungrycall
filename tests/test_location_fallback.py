"""Regression tests for the explicit restaurant source boundary."""

import httpx
import pytest
from fastapi.testclient import TestClient

from hungrycall import location, web
from hungrycall.location import (
    AddressNotFound,
    NoRestaurantsFound,
    SearchServiceUnavailable,
    search_overpass_restaurants,
)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    """Freeze 'now' at Friday 19:00 — the same fixture ``test_web.py`` uses.

    A search without a stated time is about *now*, and a closed restaurant is
    filtered out before it is called. That is correct, and it made these two
    tests depend on the hour they ran in: green over dinner, red late at night,
    when every example restaurant is shut. Freezing the clock keeps the
    correctness and drops the coin toss.
    """
    monkeypatch.setattr(web, "current_clock", lambda: "19:00")
    monkeypatch.setattr(web, "current_day", lambda: "Fri")


class StubResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


def search_form(**overrides):
    form = {
        "branch": "food",
        "mode": "delivery",
        "postcode": "10115",
        "city": "Berlin",
        "radius_km": "3.0",
        "delivery_address": "Invalidenstraße 1, 10115 Berlin",
        "first_name": "Test",
        "last_name": "User",
        "requester_callback_number": "+4917612345678",
        "food_prompt": "Burger",
        "max_budget_eur": "35.00",
        "scenario": "jury_30s_demo",
    }
    form.update(overrides)
    return form


def test_test_mode_is_explicit_and_never_contacts_the_network(monkeypatch):
    def network_must_not_run(*args, **kwargs):
        raise AssertionError("test mode attempted a network request")

    monkeypatch.setattr(location.httpx, "get", network_must_not_run)
    monkeypatch.setattr(location.httpx, "post", network_must_not_run)

    lat, lon = location.geocode_location(
        "12345", "Dorfstadt", "Deutschland", test_mode=True
    )
    restaurants = search_overpass_restaurants(
        lat, lon, radius_km=3.0, test_mode=True, city="Dorfstadt"
    )

    assert restaurants
    assert all(not restaurant.id.startswith("osm_") for restaurant in restaurants)


def test_overpass_timeout_does_not_fall_back_to_examples(monkeypatch):
    monkeypatch.setattr(
        location,
        "get_offline_restaurants",
        lambda *args, **kwargs: pytest.fail("normal mode requested example data"),
    )
    monkeypatch.setattr(
        location.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ReadTimeout("timed out")),
    )

    with pytest.raises(SearchServiceUnavailable) as error:
        search_overpass_restaurants(52.52, 13.405, radius_km=3.0)

    assert error.value.code == "service_unavailable"


def test_empty_overpass_result_has_its_own_failure(monkeypatch):
    monkeypatch.setattr(
        location.httpx, "post", lambda *args, **kwargs: StubResponse({"elements": []})
    )

    with pytest.raises(NoRestaurantsFound) as error:
        search_overpass_restaurants(52.52, 13.405, radius_km=2.5)

    assert error.value.code == "no_restaurants"


def test_overpass_identifies_hungrycall_and_requests_json(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return StubResponse({"elements": []})

    monkeypatch.setattr(location.httpx, "post", fake_post)

    with pytest.raises(NoRestaurantsFound):
        search_overpass_restaurants(52.52, 13.405, radius_km=3.0)

    assert captured["url"] == "https://overpass-api.de/api/interpreter"
    assert captured["headers"] == {
        "User-Agent": location.OSM_USER_AGENT,
        "Accept": "application/json",
    }
    assert captured["data"]["data"].strip().startswith("[out:json]")


def test_overpass_normalizes_formatted_german_phone_for_calling(monkeypatch):
    monkeypatch.setattr(
        location.httpx,
        "post",
        lambda *args, **kwargs: StubResponse(
            {
                "elements": [
                    {
                        "id": 42,
                        "lat": 52.52,
                        "lon": 13.405,
                        "tags": {
                            "name": "Fixture Bistro",
                            "phone": "03338 / 60 49 63",
                        },
                    }
                ]
            }
        ),
    )

    restaurants = search_overpass_restaurants(52.52, 13.405)

    assert restaurants[0].phone == "+493338604963"


def test_empty_geocoding_result_means_address_not_found(monkeypatch):
    monkeypatch.setattr(
        location.httpx, "get", lambda *args, **kwargs: StubResponse([])
    )

    with pytest.raises(AddressNotFound) as error:
        location.geocode_location("00000", "Unbekannt", "Deutschland")

    assert error.value.code == "address_not_found"


def test_search_page_marks_example_restaurants_in_both_languages(monkeypatch):
    def network_must_not_run(*args, **kwargs):
        raise AssertionError("test mode attempted a network request")

    monkeypatch.setattr(location.httpx, "get", network_must_not_run)
    monkeypatch.setattr(location.httpx, "post", network_must_not_run)

    for lang, label in (
        ("de", "Testmodus — Beispieldaten, keine echten Restaurants"),
        ("en", "Test mode — example data, no real restaurants"),
    ):
        with TestClient(web.app) as client:
            client.post(
                f"/restaurant-test-mode/toggle?lang={lang}&next=%2Forder",
                follow_redirects=False,
            )
            page = client.post(
                f"/api/search?lang={lang}", data=search_form()
            ).text
        assert label in page
        assert 'data-test-mode="active"' in page
        assert 'data-search-source="overpass"' not in page


def test_test_mode_stays_demonstrable_when_real_restaurants_would_be_closed(monkeypatch):
    monkeypatch.setattr(web, "current_clock", lambda: "03:00")
    monkeypatch.setattr(web, "current_day", lambda: "Sun")

    with TestClient(web.app) as client:
        client.post(
            "/restaurant-test-mode/toggle?lang=de&next=%2Forder",
            follow_redirects=False,
        )
        page = client.post("/api/search?lang=de", data=search_form()).text

    assert 'name="candidate_order"' in page
    assert "Kein Kandidat erfüllt die Vorbedingungen" not in page


def test_normal_search_page_names_overpass_and_hit_count(monkeypatch):
    pool = search_overpass_restaurants(
        52.52, 13.405, radius_km=3.0, test_mode=True, city="Dorfstadt"
    )
    monkeypatch.setattr(web, "geocode_location", lambda *args, **kwargs: (52.52, 13.405))
    monkeypatch.setattr(web, "rebuild_pool", lambda *args, **kwargs: pool)

    with TestClient(web.app) as client:
        page = client.post("/api/search?lang=de", data=search_form()).text

    assert "Quelle: OpenStreetMap via Overpass" in page
    assert f"{len(pool)} Treffer im Umkreis von 3 km" in page
    assert 'data-search-source="overpass"' in page
    assert "Testmodus — Beispieldaten" not in page


def test_all_filtered_restaurants_keep_radius_map_and_exclusion_reasons(monkeypatch):
    pool = search_overpass_restaurants(
        52.52, 13.405, radius_km=3.0, test_mode=True, city="Dorfstadt"
    )
    monkeypatch.setattr(web, "current_clock", lambda: "03:00")
    monkeypatch.setattr(web, "current_day", lambda: "Sun")
    monkeypatch.setattr(web, "geocode_location", lambda *args, **kwargs: (52.52, 13.405))
    monkeypatch.setattr(web, "rebuild_pool", lambda *args, **kwargs: pool)

    with TestClient(web.app) as client:
        page = client.post("/api/search?lang=de", data=search_form()).text

    assert "Kein Kandidat erfüllt die Vorbedingungen" in page
    assert "closed at the requested time" in page
    assert "HC.initMap(52.52, 13.405, 3.0, []);" in page
    assert 'data-search-source="overpass"' in page


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (AddressNotFound("not found"), "Adresse nicht gefunden"),
        (
            SearchServiceUnavailable("timed out"),
            "Restaurantdienst nicht erreichbar oder Zeitüberschreitung",
        ),
    ],
)
def test_geocoding_failures_are_clear_and_empty(monkeypatch, failure, expected):
    def fail_geocoding(*args, **kwargs):
        raise failure

    monkeypatch.setattr(web, "geocode_location", fail_geocoding)

    with TestClient(web.app) as client:
        page = client.post("/api/search?lang=de", data=search_form()).text

    assert expected in page
    assert 'role="alert"' in page
    assert 'name="candidate_order"' not in page
    assert "Burger House Dorfstadt" not in page


def test_no_restaurant_error_suggests_a_larger_radius(monkeypatch):
    monkeypatch.setattr(web, "geocode_location", lambda *args, **kwargs: (52.52, 13.405))

    def no_results(*args, **kwargs):
        raise NoRestaurantsFound("empty")

    monkeypatch.setattr(web, "rebuild_pool", no_results)

    with TestClient(web.app) as client:
        page = client.post("/api/search?lang=de", data=search_form(radius_km="1.5")).text

    assert "Keine Restaurants im gewählten Umkreis gefunden" in page
    assert "Vergrößere den Umkreis" in page
    assert "1.5 km" in page
    assert 'name="candidate_order"' not in page
    assert "HC.initMap(52.52, 13.405, 1.5, []);" in page


def test_restaurant_service_error_keeps_resolved_radius_map(monkeypatch):
    monkeypatch.setattr(web, "geocode_location", lambda *args, **kwargs: (52.52, 13.405))

    def service_failure(*args, **kwargs):
        raise SearchServiceUnavailable("Overpass returned HTTP 406")

    monkeypatch.setattr(web, "rebuild_pool", service_failure)

    with TestClient(web.app) as client:
        page = client.post(
            "/api/search?lang=de", data=search_form(radius_km="4.5")
        ).text

    assert "Restaurantdienst nicht erreichbar oder Zeitüberschreitung" in page
    assert "HC.initMap(52.52, 13.405, 4.5, []);" in page
    assert 'name="candidate_order"' not in page


def test_restaurant_test_mode_has_separate_on_and_off_controls():
    with TestClient(web.app) as client:
        page = client.get("/order?lang=en").text
        assert 'name="test_mode"' not in page
        assert 'data-test-mode="off"' in page
        assert "Enable test mode" in page

        enabled = client.post(
            "/restaurant-test-mode/toggle?lang=en&next=%2Forder"
        ).text
        assert 'data-test-mode="active"' in enabled
        assert "Leave test mode" in enabled

        disabled = client.post(
            "/restaurant-test-mode/toggle?lang=en&next=%2Forder"
        ).text
        assert 'data-test-mode="off"' in disabled
        assert "Enable test mode" in disabled


def test_installation_can_remove_restaurant_test_mode(monkeypatch):
    monkeypatch.setenv("HUNGRYCALL_RESTAURANT_TEST_MODE", "off")

    with TestClient(web.app) as client:
        client.cookies.set("hungrycall_restaurant_test_mode", "on")
        page = client.get("/order?lang=de").text

    assert 'data-test-mode=' not in page
    assert 'name="test_mode"' not in page
    assert "Testmodus einschalten" not in page


def test_restaurant_examples_cannot_be_combined_with_live_calls():
    with TestClient(web.app) as client:
        client.post(
            "/restaurant-test-mode/toggle?lang=de&next=%2Forder",
            follow_redirects=False,
        )
        response = client.post(
            "/api/search?lang=de",
            data=search_form(transport="live", confirm_live="yes"),
        )

    assert response.status_code == 400
    assert "Restaurant-Beispieldaten dürfen nicht für echte Anrufe verwendet werden" in response.text
