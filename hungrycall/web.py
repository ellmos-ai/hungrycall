"""FastAPI web interface for HungryCall.

Two branches, one cascade. /order asks for food (delivered or collected),
/reserve asks for a table; both end up in the same engine with different
criteria, which is the point MUSTER.md makes.

State is deliberately thin. The candidate pool is rebuilt from the submitted
form on every step instead of being parked in a module-level "latest search" —
that shared slot meant two people using the app at once overwrote each other's
restaurants.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from hungrycall.call_client import DryRunCallClient
from hungrycall.db import (
    create_order_record, init_db, list_saved_results, save_cascade_result
)
from hungrycall.engine import CascadeEngine, build_call_goal
from hungrycall.fixtures import SCENARIO_FIXTURES
from hungrycall.geo import today_weekday_key, weekday_key
from hungrycall.i18n import LANG_COOKIE, resolve_lang, t
from hungrycall.location import geocode_location, search_overpass_restaurants
from hungrycall.models import (
    Branch, Concession, Mode, Restaurant, Seating, UserRequest
)
from hungrycall.phone_utils import mask_phone
from hungrycall.ranking import filter_and_rank_restaurants, filter_candidate
from hungrycall.safety import SafetyError, generate_idempotency_key, verify_content_safety
from hungrycall.templates import (
    TABLE_CONCESSIONS, render_branch_page, render_candidate_step,
    render_cascade_monitor, render_failure, render_history, render_landing,
    render_page, render_result_card, render_result_sentence
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="I am hungry — hungrycall",
    description="Sequential voice-agent cascade on CALL-E: order food or book a table.",
)

init_db()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Per-order runtime state, only for the lifetime of one cascade.
ACTIVE_ORDERS: Dict[str, Dict[str, Any]] = {}
CANCELED_ORDERS: set = set()

DEFAULT_SCENARIOS = {
    Mode.DELIVERY: "jury_30s_demo",
    Mode.PICKUP: "pickup_cascade",
    Mode.RESERVATION: "table_cascade",
}

# How long the dry run pretends the ~40 s CALL-E setup takes. Real calls do not
# get faster because we are impatient; this is presentation, and it is labelled
# as such in the interface.
DRY_RUN_DIAL_SECONDS = 1.6
DRY_RUN_TURN_SECONDS = 0.45


# --------------------------------------------------------------------------
# Language
# --------------------------------------------------------------------------

def lang_of(request: Request, explicit: Optional[str] = None) -> str:
    return resolve_lang(
        query_lang=explicit or request.query_params.get("lang"),
        cookie_lang=request.cookies.get(LANG_COOKIE),
        accept_language=request.headers.get("accept-language"),
    )


def html_page(body: str, lang: str, **kwargs: Any) -> HTMLResponse:
    response = HTMLResponse(render_page(body, lang, **kwargs))
    response.set_cookie(LANG_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="lax")
    return response


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    lang = lang_of(request)
    return html_page(render_landing(lang), lang, path="/")


@app.get("/order", response_class=HTMLResponse)
async def order_page(request: Request):
    lang = lang_of(request)
    body = render_branch_page(
        Branch.FOOD, lang, sorted(SCENARIO_FIXTURES.keys()), DEFAULT_SCENARIOS[Mode.DELIVERY]
    )
    return html_page(body, lang, path="/order", with_map=True, title=t("food.title", lang))


@app.get("/reserve", response_class=HTMLResponse)
async def reserve_page(request: Request):
    lang = lang_of(request)
    body = render_branch_page(
        Branch.TABLE, lang, sorted(SCENARIO_FIXTURES.keys()), DEFAULT_SCENARIOS[Mode.RESERVATION]
    )
    return html_page(body, lang, path="/reserve", with_map=True, title=t("table.title", lang))


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    lang = lang_of(request)
    return html_page(
        render_history(lang, list_saved_results()), lang,
        path="/history", title=t("history.title", lang)
    )


# --------------------------------------------------------------------------
# Request building
# --------------------------------------------------------------------------

def current_clock() -> str:
    """The time a request without a stated time is about. A delivery is now."""
    return time.strftime("%H:%M")


def current_day() -> str:
    return today_weekday_key()


def build_user_request(fields: Dict[str, Any]) -> UserRequest:
    """Turn one submitted form into the request the engine works from."""
    mode = Mode(fields.get("mode") or "delivery")

    concession_keys = fields.get("concessions") or []
    concessions = [c for c in TABLE_CONCESSIONS if c.key in concession_keys]

    reservation_date = fields.get("reservation_date")
    day = (
        weekday_key(reservation_date, current_day())
        if mode is Mode.RESERVATION else current_day()
    )

    def as_float(key: str) -> Optional[float]:
        raw = fields.get(key)
        if raw in (None, "", "None"):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def as_int(key: str) -> Optional[int]:
        value = as_float(key)
        return int(value) if value is not None else None

    return UserRequest(
        mode=mode,
        customer_name=(fields.get("customer_name") or "").strip() or "Guest",
        food_prompt=(fields.get("food_prompt") or "").strip(),
        max_budget_eur=as_float("max_budget_eur") if mode is not Mode.RESERVATION else None,
        delivery_address=fields.get("delivery_address"),
        reservation_date=reservation_date,
        reservation_time=fields.get("reservation_time"),
        party_size=as_int("party_size"),
        seating=Seating(fields.get("seating") or "any"),
        pickup_time=fields.get("pickup_time") or "19:30",
        max_distance_km=as_float("max_distance_km"),
        day_of_week=day,
        time_of_request=fields.get("reservation_time") or current_clock(),
        concessions=concessions,
    )


def rebuild_pool(city: str, lat: float, lon: float, radius_km: float) -> List[Restaurant]:
    """The candidate pool for a place. Deterministic in dry run, so later steps
    can rebuild it instead of relying on a cached search."""
    return search_overpass_restaurants(
        lat=lat, lon=lon, radius_km=radius_km, dry_run=True, city=city
    )


def criteria_line(request: UserRequest, lang: str) -> str:
    """The one-line summary of what the table branch is actually testing."""
    parts = [
        f'{request.reservation_time or "?"}',
        t("candidates.seats", lang, n=request.party_size or 0),
    ]
    if request.seating is not Seating.ANY:
        parts.append(t(f"table.seating.{request.seating.value}", lang))
    return " · ".join(parts)


# --------------------------------------------------------------------------
# Step 2 — candidates
# --------------------------------------------------------------------------

@app.post("/api/search", response_class=HTMLResponse)
async def api_search(request: Request):
    form = await request.form()
    lang = lang_of(request)
    fields = {k: form.get(k) for k in form.keys()}
    branch = Branch(fields.get("branch") or "food")

    city = fields.get("city") or "Dorfstadt"
    postcode = fields.get("postcode") or ""
    radius_km = float(fields.get("radius_km") or 3.0)

    lat, lon = geocode_location(postcode, city, "Deutschland")
    pool = rebuild_pool(city, lat, lon, radius_km)

    fields["concessions"] = form.getlist("concessions")
    user_request = build_user_request(fields)

    ranked = [r for r, _ in filter_and_rank_restaurants(pool, user_request)]
    ranked_ids = {r.id for r in ranked}
    skipped = [
        (r, filter_candidate(r, user_request) or "")
        for r in pool if r.id not in ranked_ids
    ]

    # Carried forward so step 3 can rebuild everything without server-side state.
    form_state = {
        "branch": branch.value,
        "mode": fields.get("mode") or ("reservation" if branch is Branch.TABLE else "delivery"),
        "city": city,
        "postcode": postcode,
        "radius_km": radius_km,
        "scenario": fields.get("scenario") or DEFAULT_SCENARIOS[user_request.mode],
        "customer_name": user_request.customer_name,
        "food_prompt": user_request.food_prompt,
        "delivery_address": user_request.delivery_address,
        "max_budget_eur": user_request.max_budget_eur,
        "pickup_time": user_request.pickup_time,
        "max_distance_km": user_request.max_distance_km,
        "reservation_date": user_request.reservation_date,
        "reservation_time": user_request.reservation_time,
        "party_size": user_request.party_size,
        "seating": user_request.seating.value,
        "concessions": [c.key for c in user_request.concessions],
    }

    return HTMLResponse(render_candidate_step(
        lang=lang, branch=branch, ranked=ranked, skipped=skipped,
        lat=lat, lon=lon, radius_km=radius_km, form_state=form_state,
    ))


@app.post("/api/preview-goal", response_class=JSONResponse)
async def api_preview_goal(request: Request):
    """The exact text that will leave the building — from the same function
    that builds it for real, never a copy of it written in JavaScript."""
    form = await request.form()
    fields = {k: form.get(k) for k in form.keys()}
    fields["concessions"] = form.getlist("concessions")
    lang = lang_of(request)

    try:
        user_request = build_user_request(fields)
        verify_content_safety(user_request.food_prompt)
    except SafetyError:
        return JSONResponse({"error": t("error.unsafe.content", lang)}, status_code=400)
    except (ValueError, KeyError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    pool = rebuild_pool(fields.get("city") or "Dorfstadt", 52.52, 13.405,
                        float(fields.get("radius_km") or 3.0))
    order = [i for i in (fields.get("candidate_order") or "").split(",") if i]
    first = next((r for r in pool if r.id == order[0]), pool[0]) if order else pool[0]

    return JSONResponse({"goal": build_call_goal(first, user_request), "restaurant": first.name})


# --------------------------------------------------------------------------
# Step 3 — the cascade
# --------------------------------------------------------------------------

@app.post("/api/start-cascade", response_class=HTMLResponse)
async def start_cascade(request: Request):
    form = await request.form()
    lang = lang_of(request)
    fields = {k: form.get(k) for k in form.keys()}
    fields["concessions"] = form.getlist("concessions")

    branch = Branch(fields.get("branch") or "food")
    city = fields.get("city") or "Dorfstadt"
    radius_km = float(fields.get("radius_km") or 3.0)
    lat, lon = geocode_location(fields.get("postcode") or "", city, "Deutschland")

    try:
        user_request = build_user_request(fields)
        verify_content_safety(user_request.food_prompt)
    except SafetyError:
        return HTMLResponse(
            f'<div class="notice warn" style="margin-top:1rem;">{t("error.unsafe.content", lang)}</div>'
        )

    pool = rebuild_pool(city, lat, lon, radius_km)
    by_id = {r.id: r for r in pool}

    # The order the user sees is the order we call. Anything unchecked is gone.
    selected = set(form.getlist("selected_restaurants"))
    ordered_ids = [i for i in (fields.get("candidate_order") or "").split(",") if i]
    call_order = [by_id[i] for i in ordered_ids if i in by_id and i in selected]

    if not call_order:
        return HTMLResponse(
            f'<div class="notice warn" style="margin-top:1rem;">{t("candidates.none", lang)}</div>'
        )

    scenario = fields.get("scenario") or DEFAULT_SCENARIOS[user_request.mode]
    order_id = f"ord_{uuid.uuid4().hex[:8]}"

    create_order_record(
        order_id=order_id,
        mode=user_request.mode.value,
        customer_name=user_request.customer_name,
        food_prompt=user_request.food_prompt,
        max_budget_eur=user_request.max_budget_eur,
        delivery_address=user_request.delivery_address,
        reservation_date=user_request.reservation_date,
        reservation_time=user_request.reservation_time,
        party_size=user_request.party_size,
        pickup_time=user_request.pickup_time,
        location_info=city,
        dry_run=True,
    )

    ACTIVE_ORDERS[order_id] = {
        "request": user_request,
        "candidates": call_order,
        "scenario": scenario,
        "branch": branch,
    }

    return HTMLResponse(render_cascade_monitor(
        lang=lang,
        order_id=order_id,
        mode=user_request.mode,
        max_budget_eur=user_request.max_budget_eur,
        criteria_line=criteria_line(user_request, lang),
        concession_keys=[c.key for c in user_request.concessions],
    ))


def sse(payload: Dict[str, Any]) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


@app.get("/api/cascade-stream")
async def cascade_stream(request: Request, order_id: str = Query(...)):
    """Run the cascade and narrate it.

    The events are data, not markup: the client decides what a rejection looks
    like. That keeps the wire format testable without a browser.
    """
    lang = lang_of(request)
    order = ACTIVE_ORDERS.get(order_id)

    if not order:
        async def gone():
            yield sse({"type": "status", "text": t("cascade.exhausted", lang)})
            yield sse({"type": "done"})
        return StreamingResponse(gone(), media_type="text/event-stream")

    user_request: UserRequest = order["request"]
    candidates: List[Restaurant] = order["candidates"]
    client = DryRunCallClient(scenario_name=order["scenario"])
    engine = CascadeEngine(candidate_pool=candidates, call_client=client, preserve_order=True)

    async def event_generator():
        yield sse({"type": "status", "text": t("cascade.init", lang)})
        await asyncio.sleep(0.3)

        calls_made = 0

        for restaurant in candidates:
            if order_id in CANCELED_ORDERS:
                yield sse({"type": "canceled", "text": t("cascade.canceled", lang)})
                return

            yield sse({
                "type": "dialing",
                "id": restaurant.id,
                "text": t("cascade.dialing", lang, name=restaurant.name),
            })
            await asyncio.sleep(DRY_RUN_DIAL_SECONDS)

            if order_id in CANCELED_ORDERS:
                yield sse({"type": "canceled", "text": t("cascade.canceled", lang)})
                return

            call_result = client.execute_candidate_call(
                restaurant=restaurant,
                user_request=user_request,
                idempotency_key=generate_idempotency_key(
                    user_request.mode.value, restaurant.id, time.time()
                ),
            )
            calls_made += 1

            yield sse({
                "type": "connected",
                "id": restaurant.id,
                "text": t("cascade.talking", lang, name=restaurant.name),
            })

            for line in call_result.activity:
                if order_id in CANCELED_ORDERS:
                    yield sse({"type": "canceled", "text": t("cascade.canceled", lang)})
                    return
                yield sse({"type": "activity", "id": restaurant.id, "line": line})
                await asyncio.sleep(DRY_RUN_TURN_SECONDS)

            passed, rejection_reason = engine.evaluate_result(user_request, call_result)

            if not passed:
                yield sse({
                    "type": "rejected",
                    "id": restaurant.id,
                    "label": t("cascade.rejected", lang),
                    "reason": rejection_reason or "",
                })
                await asyncio.sleep(0.4)
                continue

            concession_used = call_result.structured_result.get("tier_applied") or None
            yield sse({"type": "accepted", "id": restaurant.id})

            ACTIVE_ORDERS[order_id]["result"] = {
                "restaurant": restaurant,
                "call_result": call_result,
                "calls_made": calls_made,
            }

            yield sse({
                "type": "outcome",
                "text": t("cascade.done", lang),
                "html": render_result_card(
                    lang=lang,
                    mode=user_request.mode,
                    restaurant=restaurant,
                    structured=call_result.structured_result,
                    post_summary=call_result.post_summary,
                    raw_transcript_text=call_result.raw_transcript_text or "",
                    message=render_result_sentence(
                        lang=lang,
                        mode=user_request.mode,
                        restaurant=restaurant,
                        structured=call_result.structured_result,
                        food_prompt=user_request.food_prompt,
                        party_size=user_request.party_size,
                        reservation_date=user_request.reservation_date,
                        reservation_time=user_request.reservation_time,
                    ),
                    order_id=order_id,
                    calls_made=calls_made,
                    concession_used=concession_used,
                ),
            })
            yield sse({"type": "done"})
            return

        yield sse({
            "type": "outcome",
            "text": t("cascade.done", lang),
            "html": render_failure(lang, calls_made),
        })
        yield sse({"type": "done"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/cancel-cascade", response_class=HTMLResponse)
async def cancel_cascade(request: Request, order_id: str = Form(...)):
    """Stop before the next number is dialled."""
    CANCELED_ORDERS.add(order_id)
    lang = lang_of(request)
    return HTMLResponse(f'<span class="mono">{t("cascade.canceled", lang)}</span>')


# --------------------------------------------------------------------------
# Saving
# --------------------------------------------------------------------------

@app.post("/api/save-result", response_class=HTMLResponse)
async def api_save_result(
    request: Request,
    order_id: str = Form(...),
    restaurant_id: str = Form(""),
):
    """Keep the result of a finished cascade.

    Everything is read back from the run itself. The earlier version took the
    numbers from hidden form fields and wrote mode='delivery' regardless of
    what had actually happened, so a booked table was filed as a food order.
    """
    lang = lang_of(request)
    order = ACTIVE_ORDERS.get(order_id) or {}
    finished = order.get("result")

    if not finished:
        return HTMLResponse(f'<span class="mono">{t("history.empty", lang)}</span>')

    restaurant: Restaurant = finished["restaurant"]
    call_result = finished["call_result"]
    user_request: UserRequest = order["request"]
    structured = call_result.structured_result

    save_cascade_result(
        result_id=f"res_{uuid.uuid4().hex[:8]}",
        order_id=order_id,
        mode=user_request.mode.value,
        restaurant_id=restaurant_id or restaurant.id,
        restaurant_name=restaurant.name,
        masked_phone=mask_phone(structured.get("callback_number") or restaurant.phone),
        callback_number=structured.get("callback_number") or restaurant.phone,
        total_price_eur=structured.get("total_price_eur"),
        eta_minutes=structured.get("eta_minutes") or structured.get("prep_time_minutes"),
        post_summary=call_result.post_summary,
        raw_transcript_text=call_result.raw_transcript_text,
        structured_result=structured,
    )
    return HTMLResponse(f'<span class="mono">{t("result.saved", lang)}</span>')


@app.get("/api/saved-results", response_class=JSONResponse)
async def api_get_saved_results():
    return list_saved_results()


def main():
    """CLI entrypoint to run the HungryCall web server."""
    import uvicorn
    print("Starting HungryCall on http://127.0.0.1:8000 ...")
    uvicorn.run("hungrycall.web:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
