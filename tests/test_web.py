"""Unit and integration tests for HungryCall Web UI, DB, Location, and FastAPI routes."""

import os
import pytest
from fastapi.testclient import TestClient

from hungrycall.db import init_db, create_order_record, save_cascade_result, list_saved_results
from hungrycall.location import geocode_location, search_overpass_restaurants, get_offline_restaurants
from hungrycall.web import app


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Use isolated temporary database for tests."""
    db_file = str(tmp_path / "test_hungrycall.db")
    os.environ["HUNGRYCALL_DB_PATH"] = db_file
    init_db(db_file)
    yield db_file
    if "HUNGRYCALL_DB_PATH" in os.environ:
        del os.environ["HUNGRYCALL_DB_PATH"]


def test_db_order_and_save_result(setup_test_db):
    """Test SQLite database order creation and result persistence."""
    order = create_order_record(
        order_id="test_ord_1",
        mode="delivery",
        customer_name="Lukas Test",
        food_prompt="Burger and Fries",
        max_budget_eur=30.0,
        delivery_address="Test Str 1, 12345 Dorfstadt"
    )
    assert order["id"] == "test_ord_1"
    assert order["customer_name"] == "Lukas Test"

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
        raw_transcript_text="[00:05] BOT: Hello\n[00:10] USER: Yes",
        structured_result={"order_placed": True}
    )
    assert saved["id"] == "test_res_1"
    assert saved["restaurant_name"] == "Burger House Dorfstadt"

    history = list_saved_results()
    assert len(history) == 1
    assert history[0]["customer_name"] == "Lukas Test"
    assert history[0]["callback_number"] == "+491701111111"


def test_location_geocoding_and_fixtures():
    """Test international location geocoding and offline restaurant pools."""
    # Test Singapore
    sg_lat, sg_lon = geocode_location("730123", "Singapore", "Singapore")
    assert abs(sg_lat - 1.3521) < 0.1
    sg_rests = get_offline_restaurants("Singapore")
    assert len(sg_rests) > 0
    assert any("Hawker" in r.name or "Din Tai Fung" in r.name for r in sg_rests)

    # Test Default Dorfstadt
    df_lat, df_lon = geocode_location("12345", "Dorfstadt", "Deutschland")
    assert abs(df_lat - 52.5200) < 0.1
    df_rests = search_overpass_restaurants(df_lat, df_lon, dry_run=True, city="Dorfstadt")
    assert len(df_rests) >= 3


def test_fastapi_web_routes():
    """Test FastAPI endpoint responses."""
    client = TestClient(app)

    # 1. Main Page
    response = client.get("/")
    assert response.status_code == 200
    assert "I am hungry" in response.text
    assert "Leaflet" in response.text or "leaflet.js" in response.text

    # 2. Search Endpoint
    search_resp = client.post(
        "/api/search",
        data={
            "postcode": "12345",
            "city": "Dorfstadt",
            "country": "Deutschland",
            "delivery_address": "Dorfstraße 10, 12345 Dorfstadt",
            "radius_km": "3.0",
            "dry_run": "true"
        }
    )
    assert search_resp.status_code == 200
    assert "Restaurantauswahl" in search_resp.text
    assert "Burger House Dorfstadt" in search_resp.text

    # 3. Start Cascade Endpoint
    cascade_resp = client.post(
        "/api/start-cascade",
        data={
            "mode": "delivery",
            "customer_name": "Lukas Test",
            "food_prompt": "Pizza Margherita",
            "max_budget_eur": "25.00",
            "city": "Dorfstadt",
            "delivery_address": "Marktplatz 5",
            "selected_restaurants": ["rest_trattoria_luigi"]
        }
    )
    assert cascade_resp.status_code == 200
    assert "Anruf-Kaskade läuft live" in cascade_resp.text

    # 4. Save Result Endpoint
    save_resp = client.post(
        "/api/save-result",
        data={
            "order_id": "ord_test_99",
            "restaurant_name": "Trattoria Bella Luigi",
            "callback_number": "+491702222222",
            "total_price_eur": "22.50",
            "eta_minutes": "40",
            "post_summary": "Order confirmed",
            "raw_transcript_text": "Transcript content..."
        }
    )
    assert save_resp.status_code == 200
    assert "gespeichert" in save_resp.text

    # 5. Get Saved Results Endpoint
    get_saved_resp = client.get("/api/saved-results")
    assert get_saved_resp.status_code == 200
    results_json = get_saved_resp.json()
    assert isinstance(results_json, list)


def test_video_backflow_radius_and_budget_band():
    """Test video backflow features: radius circle, budget band banner, and transcript price badge."""
    client = TestClient(app)

    # 1. Search with radius_km
    search_resp = client.post(
        "/api/search",
        data={
            "postcode": "12345",
            "city": "Dorfstadt",
            "country": "Deutschland",
            "delivery_address": "Hauptstr. 1",
            "radius_km": "5.0",
            "dry_run": "true"
        }
    )
    assert search_resp.status_code == 200
    assert "initLeafletMap(52.52, 13.405, 13, 5.0)" in search_resp.text
    assert "rejection-rest_burger_house" in search_resp.text

    # 2. Start Cascade with Financial Authority Cap Band
    cascade_resp = client.post(
        "/api/start-cascade",
        data={
            "mode": "delivery",
            "customer_name": "Lukas Backflow",
            "food_prompt": "Burger",
            "max_budget_eur": "35.00",
            "city": "Dorfstadt",
            "delivery_address": "Hauptstr. 1",
            "selected_restaurants": ["rest_burger_house"]
        }
    )
    assert cascade_resp.status_code == 200
    assert "FINANCIAL AUTHORITY CAP" in cascade_resp.text
    assert "Höchstbetrag: 35.00 €" in cascade_resp.text

    # 3. Render Result Card with Transcript Price Badge
    from hungrycall.templates import render_result_card
    card_html = render_result_card(
        restaurant_name="Burger House",
        callback_number="+491701111111",
        total_price_eur=28.50,
        eta_minutes=30,
        post_summary="Ordered",
        raw_transcript_text="[00:05] BOT: Hi\n[00:10] USER: 28.50 EUR",
        order_id="test_ord_bf"
    )
    assert "Bestätigter Transkript-Endpreis:" in card_html
    assert "28.50 €" in card_html
    assert "In Budget" in card_html

