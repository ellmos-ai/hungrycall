"""FastAPI Web Application and SSE Stream Server for HungryCall."""

import asyncio
import json
import logging
import os
import uuid
import time
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Form, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from hungrycall.models import (
    Restaurant, Mode, UserRequest, CallStatus, AttemptRecord, CascadeSummary
)
from hungrycall.location import geocode_location, search_overpass_restaurants, get_offline_restaurants
from hungrycall.engine import CascadeEngine, build_call_goal
from hungrycall.call_client import DryRunCallClient
from hungrycall.db import init_db, create_order_record, save_cascade_result, list_saved_results
from hungrycall.templates import (
    render_base_page, render_search_loading,
    render_restaurant_selection_step, render_cascade_monitor, render_result_card
)

logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="I am hungry — hungrycall Web UI",
    description="FastAPI + HTMX + SQLite Web Interface for CALL-E sequential voice agent cascade."
)

# Ensure database tables exist on startup
init_db()

# Mount static files directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory store for active session state (orders & cancellation flags)
ACTIVE_ORDERS: Dict[str, Dict[str, Any]] = {}
CANCELED_ORDERS: set = set()


@app.get("/", response_class=HTMLResponse)
async def index():
    """Render base application HTML shell with HTMX and Leaflet map."""
    return render_base_page()


@app.post("/api/search", response_class=HTMLResponse)
async def api_search(
    postcode: str = Form("12345"),
    city: str = Form("Dorfstadt"),
    country: str = Form("Deutschland"),
    delivery_address: str = Form("Dorfstraße 10, 12345 Dorfstadt"),
    radius_km: float = Form(3.0),
    dry_run: str = Form("true")
):
    """Handle restaurant search form submission with geocoding and Overpass query."""
    is_dry_run = (dry_run.lower() == "true")
    
    # 1. Geocode location
    lat, lon = geocode_location(postcode, city, country)
    
    # 2. Search restaurants (live Overpass or offline fixtures)
    restaurants = search_overpass_restaurants(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        dry_run=is_dry_run,
        city=city
    )
    
    # Store search results in session cache
    ACTIVE_ORDERS["latest_search"] = {
        "lat": lat,
        "lon": lon,
        "city": city,
        "delivery_address": delivery_address,
        "restaurants": restaurants
    }

    # Render Step 2 HTML
    return render_restaurant_selection_step(
        restaurants=restaurants,
        lat=lat,
        lon=lon,
        city=city,
        delivery_address=delivery_address,
        radius_km=radius_km
    )


@app.post("/api/start-cascade", response_class=HTMLResponse)
async def start_cascade(
    request: Request,
    mode: str = Form("delivery"),
    customer_name: str = Form("Alex"),
    food_prompt: str = Form("2x Cheeseburger, 1x Große Pommes, 1x Cola Zero"),
    max_budget_eur: Optional[float] = Form(35.00),
    city: str = Form("Dorfstadt"),
    delivery_address: str = Form("Dorfstraße 10, 12345 Dorfstadt"),
    selected_restaurants: List[str] = Form([])
):
    """Initialize cascade order in SQLite database and return SSE monitor container."""
    order_id = f"ord_{uuid.uuid4().hex[:8]}"
    
    # Retrieve cached restaurant pool from latest search
    latest = ACTIVE_ORDERS.get("latest_search", {})
    all_restaurants: List[Restaurant] = latest.get("restaurants", get_offline_restaurants(city))
    
    # Filter restaurants by user selections if specified
    if selected_restaurants:
        chosen_pool = [r for r in all_restaurants if r.id in selected_restaurants]
    else:
        chosen_pool = all_restaurants

    # Fallback default if empty selection
    if not chosen_pool:
        chosen_pool = get_offline_restaurants(city)

    # Save order parameters to SQLite database
    create_order_record(
        order_id=order_id,
        mode=mode,
        customer_name=customer_name,
        food_prompt=food_prompt,
        max_budget_eur=max_budget_eur,
        delivery_address=delivery_address,
        location_info=city,
        dry_run=True
    )

    # Cache order details for SSE runner
    ACTIVE_ORDERS[order_id] = {
        "mode": Mode(mode),
        "customer_name": customer_name,
        "food_prompt": food_prompt,
        "max_budget_eur": max_budget_eur,
        "delivery_address": delivery_address,
        "city": city,
        "chosen_pool": chosen_pool
    }

    return render_cascade_monitor(order_id=order_id, dry_run=True, max_budget_eur=max_budget_eur)


@app.get("/api/cascade-stream")
async def cascade_stream(order_id: str = Query(...), dry_run: str = Query("true")):
    """
    SSE Live Stream endpoint that executes the calling cascade step-by-step.
    Updates stationary restaurant cards with moving 📞 telephone handset icon,
    streams real-time activity logs, and emits final Result Card HTML.
    """
    order_info = ACTIVE_ORDERS.get(order_id)
    if not order_info:
        # Fallback default order info
        order_info = {
            "mode": Mode.DELIVERY,
            "customer_name": "Alex",
            "food_prompt": "2x Cheeseburger, 1x Große Pommes, 1x Cola Zero",
            "max_budget_eur": 35.00,
            "delivery_address": "Dorfstraße 10, 12345 Dorfstadt",
            "city": "Dorfstadt",
            "chosen_pool": get_offline_restaurants("Dorfstadt")
        }

    user_req = UserRequest(
        mode=order_info["mode"],
        customer_name=order_info["customer_name"],
        food_prompt=order_info["food_prompt"],
        max_budget_eur=order_info["max_budget_eur"],
        delivery_address=order_info["delivery_address"]
    )
    
    candidate_pool: List[Restaurant] = order_info["chosen_pool"]
    client = DryRunCallClient(scenario_name="vague_price_cascade")
    engine = CascadeEngine(candidate_pool=candidate_pool, call_client=client)

    async def event_generator():
        # Yield initial SSE connection confirmation
        yield "data: " + json.dumps({"type": "init", "message": "Cascade stream connected."}) + "\n\n"
        await asyncio.sleep(0.5)

        for idx, restaurant in enumerate(candidate_pool):
            if order_id in CANCELED_ORDERS:
                yield "data: " + json.dumps({
                    "type": "canceled",
                    "html": "<div style='color: #ef4444; font-weight: 600; padding: 0.5rem;'>⛔ Kaskade vom Nutzer abgebrochen.</div>"
                }) + "\n\n"
                return

            # 1. Update Handset Icon to Gray Pulsing (Dialing / ~40s lead-time)
            yield "data: " + json.dumps({
                "type": "call_preparing",
                "restaurant_id": restaurant.id,
                "restaurant_name": restaurant.name,
                "html": f"""
                <script>
                    document.getElementById('cascade-status-text').innerText = "Wähle {restaurant.name}... ~40s Vorlaufzeit (Gespräch wird aufgebaut)";
                    const hs = document.getElementById('handset-{restaurant.id}');
                    if (hs) hs.innerHTML = '<span class="handset-status gray" title="Anruf wird aufgebaut...">📞</span>';
                </script>
                """
            }) + "\n\n"

            # Simulate ~40s setup latency smoothly in dry-run mode (fast-forwarded to 2s for responsive UX)
            await asyncio.sleep(1.8)

            # 2. Execute Candidate Call
            call_res = client.execute_candidate_call(
                restaurant=restaurant,
                user_request=user_req,
                idempotency_key=f"web_key_{restaurant.id}_{int(time.time())}"
            )

            # 3. Stream real-time activity log turns if connected
            if call_res.activity:
                yield "data: " + json.dumps({
                    "type": "call_connected",
                    "restaurant_id": restaurant.id,
                    "html": f"""
                    <script>
                        document.getElementById('cascade-status-text').innerText = "Gespräch steht mit {restaurant.name}!";
                        const hs = document.getElementById('handset-{restaurant.id}');
                        if (hs) hs.innerHTML = '<span class="handset-status green" title="Gespräch aktiv">📞</span>';
                    </script>
                    """
                }) + "\n\n"
                await asyncio.sleep(1.0)

            # 4. Evaluate Result
            passed, rejection_reason = engine.evaluate_result(user_req, call_res)

            if passed:
                # SUCCESS! Update UI with success icon, render result card, end stream
                cb_num = call_res.structured_result.get("callback_number", restaurant.phone)
                price = call_res.structured_result.get("total_price_eur", 29.00)
                eta = call_res.structured_result.get("eta_minutes", 45)
                post_sum = call_res.post_summary
                raw_trans = call_res.raw_transcript_text or ""

                result_card_html = render_result_card(
                    restaurant_name=restaurant.name,
                    callback_number=cb_num,
                    total_price_eur=price,
                    eta_minutes=eta,
                    post_summary=post_sum,
                    raw_transcript_text=raw_trans,
                    order_id=order_id
                )

                yield "data: " + json.dumps({
                    "type": "cascade_success",
                    "restaurant_id": restaurant.id,
                    "html": f"""
                    <script>
                        document.getElementById('cascade-status-text').innerText = "Bestellung erfolgreich abgeschlossen!";
                        const hs = document.getElementById('handset-{restaurant.id}');
                        if (hs) hs.innerHTML = '<span class="handset-status" style="color: #10b981;">✅</span>';
                        
                        const card = document.getElementById('rest-card-{restaurant.id}');
                        if (card) card.classList.add('success-active');
                        
                        // Increment call counter
                        callCount += {idx + 1};
                        document.getElementById('call-counter').innerText = callCount;
                    </script>
                    <div style="margin-top: 1rem;">
                        {result_card_html}
                    </div>
                    """
                }) + "\n\n"
                return

            else:
                # REJECTED / FAILED: Strike through card, display inline rejection badge, move handset to next
                yield "data: " + json.dumps({
                    "type": "call_failed",
                    "restaurant_id": restaurant.id,
                    "rejection_reason": rejection_reason,
                    "html": f"""
                    <script>
                        const hs = document.getElementById('handset-{restaurant.id}');
                        if (hs) hs.innerHTML = '<span class="handset-status" style="color: #ef4444;" title="{rejection_reason}">❌</span>';
                        
                        const card = document.getElementById('rest-card-{restaurant.id}');
                        if (card) card.classList.add('struck-through');

                        const rejBox = document.getElementById('rejection-{restaurant.id}');
                        if (rejBox) rejBox.innerHTML = '<div style="color: #f87171; font-size: 0.78rem; font-weight: 500;">🔴 Abgelehnt: {rejection_reason}</div>';
                    </script>
                    """
                }) + "\n\n"
                await asyncio.sleep(0.8)

        # Candidates exhausted
        yield "data: " + json.dumps({
            "type": "cascade_failed",
            "html": "<div style='color: #ef4444; padding: 0.5rem;'>❌ Alle Kandidaten durchlaufen, aber keine Bestellung entsprach den Kriterien.</div>"
        }) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/cancel-cascade", response_class=HTMLResponse)
async def cancel_cascade(order_id: str = Form(...)):
    """Cancel active cascade execution."""
    CANCELED_ORDERS.add(order_id)
    return "<div style='color: #ef4444; font-weight: 600; padding: 0.5rem;'>⛔ Kaskade wurde abgebrochen.</div>"


@app.post("/api/save-result", response_class=HTMLResponse)
async def api_save_result(
    order_id: str = Form(...),
    restaurant_name: str = Form(...),
    callback_number: str = Form(...),
    total_price_eur: float = Form(...),
    eta_minutes: int = Form(...),
    post_summary: str = Form(...),
    raw_transcript_text: str = Form(...)
):
    """Save final successful cascade result to SQLite database."""
    res_id = f"res_{uuid.uuid4().hex[:8]}"
    save_cascade_result(
        result_id=res_id,
        order_id=order_id,
        mode="delivery",
        restaurant_id="rest_saved",
        restaurant_name=restaurant_name,
        masked_phone=callback_number[:6] + "...",
        callback_number=callback_number,
        total_price_eur=total_price_eur,
        eta_minutes=eta_minutes,
        post_summary=post_summary,
        raw_transcript_text=raw_transcript_text,
        structured_result={"order_placed": True}
    )
    return "✅ In SQLite gespeichert!"


@app.get("/api/saved-results", response_class=JSONResponse)
async def api_get_saved_results():
    """Retrieve saved results from SQLite database."""
    return list_saved_results()


def main():
    """CLI entrypoint to run hungrycall web server."""
    import uvicorn
    print("Starting HungryCall Web UI on http://127.0.0.1:8000 ...")
    uvicorn.run("hungrycall.web:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
