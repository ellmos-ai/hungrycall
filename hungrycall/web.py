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
import html
import json
import logging
import math
import os
import time
import uuid
from typing import Any

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

from hungrycall import (
    field_trial,
    huckepack_storage,
    huckepack_web,
    restaurant_test_mode,
)
from hungrycall.call_client import CalleAPIError, DryRunCallClient, LiveCallClient
from hungrycall.calle_key import resolve_call_settings
from hungrycall.db import (
    create_order_record,
    get_order_record,
    get_order_template,
    init_db,
    list_call_attempts,
    list_order_records,
    list_order_templates,
    list_saved_results,
    list_tags,
    record_call_attempt,
    save_cascade_result,
    save_order_template,
    save_tags,
)
from hungrycall.engine import CascadeEngine, build_call_goal, classify_rejection
from hungrycall.fixtures import SCENARIO_FIXTURES
from hungrycall.geo import today_weekday_key, weekday_key
from hungrycall.i18n import LANG_COOKIE, resolve_lang, t
from hungrycall.location import (
    RestaurantSearchError,
    geocode_location,
    search_overpass_restaurants,
)
from hungrycall.models import Branch, CallResult, Mode, Restaurant, Seating, UserRequest
from hungrycall.order_chains import (
    default_order_chain,
    evaluate_order_chain,
    order_chain_json,
    parse_order_chain,
)
from hungrycall.phone_utils import (
    mask_phone,
    mask_phones_in_text,
    normalize_e164,
    validate_e164,
)
from hungrycall.ranking import filter_and_rank_restaurants, filter_candidate
from hungrycall.safety import (
    SafetyError,
    generate_idempotency_key,
    verify_content_safety,
)
from hungrycall.server_mode import current_mode
from hungrycall.templates import (
    FOOD_CONCESSIONS,
    render_branch_page,
    render_candidate_step,
    render_cascade_monitor,
    render_failure,
    render_history,
    render_landing,
    render_page,
    render_result_card,
    render_result_sentence,
    render_search_error,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="I am hungry — hungrycall",
    description="Sequential voice-agent cascade on CALL-E: order food or book a table.",
)

huckepack_web.install(app)

init_db()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Per-order runtime state, only for the lifetime of one cascade.
ACTIVE_ORDERS: dict[str, dict[str, Any]] = {}
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

def lang_of(request: Request, explicit: str | None = None) -> str:
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
async def order_page(
    request: Request,
    history: str | None = Query(None),
    template: str | None = Query(None),
):
    lang = lang_of(request)
    loaded_order = get_order_record(history) if history else None
    loaded_template = get_order_template(template) if template else None
    initial_chain = parse_order_chain(
        (loaded_order or {}).get("order_chain")
        or (loaded_template or {}).get("order_chain")
    ) or default_order_chain()
    defaults = loaded_order or {}
    test_mode_active = restaurant_test_mode.active(request.cookies)
    body = render_branch_page(
        Branch.FOOD, lang, sorted(SCENARIO_FIXTURES.keys()), DEFAULT_SCENARIOS[Mode.DELIVERY],
        order_chain=initial_chain,
        tags=list_tags(),
        order_templates=list_order_templates(),
        defaults=defaults,
        test_mode_active=test_mode_active,
    )
    mode_banner = ""
    if restaurant_test_mode.feature_enabled():
        mode_banner = restaurant_test_mode.banner(
            test_mode_active, lang, "/order"
        )
    return html_page(
        body, lang, path="/order", with_map=True, title=t("food.title", lang),
        mode_banner=mode_banner,
    )


@app.get("/reserve", response_class=HTMLResponse)
async def reserve_page(request: Request):
    lang = lang_of(request)
    test_mode_active = restaurant_test_mode.active(request.cookies)
    body = render_branch_page(
        Branch.TABLE, lang, sorted(SCENARIO_FIXTURES.keys()), DEFAULT_SCENARIOS[Mode.RESERVATION],
        test_mode_active=test_mode_active,
    )
    mode_banner = ""
    if restaurant_test_mode.feature_enabled():
        mode_banner = restaurant_test_mode.banner(
            test_mode_active, lang, "/reserve"
        )
    return html_page(
        body, lang, path="/reserve", with_map=True, title=t("table.title", lang),
        mode_banner=mode_banner,
    )


@app.post("/restaurant-test-mode/toggle")
async def toggle_restaurant_test_mode(request: Request):
    """Switch the fixture-only restaurant workspace on or off for this browser."""
    lang = lang_of(request)
    target = restaurant_test_mode.safe_return_path(request.query_params.get("next"))
    separator = "&" if "?" in target else "?"
    response = RedirectResponse(f"{target}{separator}lang={lang}", status_code=303)
    if not restaurant_test_mode.feature_enabled():
        response.delete_cookie(restaurant_test_mode.COOKIE_NAME)
        return response
    if restaurant_test_mode.active(request.cookies):
        response.delete_cookie(restaurant_test_mode.COOKIE_NAME)
    else:
        response.set_cookie(
            restaurant_test_mode.COOKIE_NAME,
            "on",
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite="lax",
        )
    return response


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    lang = lang_of(request)
    return html_page(
        render_history(lang, list_saved_results(), list_order_records()), lang,
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


def build_user_request(
    fields: dict[str, Any],
    *,
    day_override: str | None = None,
    time_override: str | None = None,
) -> UserRequest:
    """Turn one submitted form into the request the engine works from."""
    mode = Mode(fields.get("mode") or "delivery")

    concession_keys = fields.get("concessions") or []
    concessions = (
        [] if mode is Mode.RESERVATION
        else [c for c in FOOD_CONCESSIONS if c.key in concession_keys]
    )

    reservation_date = fields.get("reservation_date")
    current_day_value = day_override or current_day()
    day = (
        weekday_key(reservation_date, current_day_value)
        if mode is Mode.RESERVATION else current_day_value
    )

    def as_float(key: str) -> float | None:
        raw = fields.get(key)
        if raw in (None, "", "None"):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def as_int(key: str) -> int | None:
        value = as_float(key)
        return int(value) if value is not None else None

    def bounded_int(key: str, maximum: int) -> int:
        raw = fields.get(key)
        if raw in (None, "", "None"):
            return 0
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} must be a whole number") from exc
        if value < 0 or value > maximum:
            raise ValueError(f"{key} must be between 0 and {maximum}")
        return value

    legacy_name = str(fields.get("customer_name") or "").strip()
    first_name = str(fields.get("first_name") or "").strip()
    last_name = str(fields.get("last_name") or "").strip()
    if not first_name and not last_name and legacy_name:
        name_parts = legacy_name.split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
    if not first_name:
        raise ValueError("first_name is required")
    if not last_name:
        # The form already marks the field required; the server must not be
        # weaker. A delivery or reservation needs a full name the restaurant
        # can work with — "Alex" alone helps nobody at the doorbell.
        raise ValueError("last_name is required")
    customer_name = " ".join(part for part in (first_name, last_name) if part)

    raw_callback = str(fields.get("requester_callback_number") or "").strip()
    requester_callback_number = normalize_e164(raw_callback) if raw_callback else ""
    if not validate_e164(requester_callback_number):
        raise ValueError("requester_callback_number must use a valid E.164 phone number")

    earlier_hours = bounded_int("earlier_hours", 3)
    later_hours = bounded_int("later_hours", 3)
    earlier_minutes = bounded_int("earlier_minutes", 59)
    later_minutes = bounded_int("later_minutes", 59)

    raw_booking_fee = fields.get("max_booking_fee_eur")
    if raw_booking_fee in (None, "", "None"):
        max_booking_fee_eur = 0.0
    else:
        try:
            max_booking_fee_eur = float(raw_booking_fee)
        except (TypeError, ValueError) as exc:
            raise ValueError("max_booking_fee_eur must be numeric") from exc
    if (
        not math.isfinite(max_booking_fee_eur)
        or max_booking_fee_eur < 0
        or max_booking_fee_eur > 1000
    ):
        raise ValueError("max_booking_fee_eur must be between 0 and 1000")

    def optional_text(key: str, maximum: int) -> str | None:
        value = str(fields.get(key) or "").strip()
        if len(value) > maximum:
            raise ValueError(f"{key} must be at most {maximum} characters")
        return value or None

    chain = parse_order_chain(fields.get("order_chain_json")) if mode is not Mode.RESERVATION else None
    food_prompt = chain.summary() if chain else (fields.get("food_prompt") or "").strip()

    seating = Seating(fields.get("seating") or "any")
    seating_custom = optional_text("seating_custom", 200)
    if seating is Seating.CUSTOM and not seating_custom:
        raise ValueError("seating_custom is required when custom seating is selected")
    if seating is not Seating.CUSTOM and seating_custom:
        raise ValueError("seating_custom requires custom seating to be selected")

    # Coverage-map finding #22 (CONVERSATION-TREE.md §4 row 22): build_call_goal
    # only ever renders special_instructions inside the RESERVATION branch
    # (special_clause). There is no delivery/pickup web field for it today, so
    # this used to be reachable only by hand-crafting a request -- but nothing
    # here stopped that request from being accepted and the note silently
    # dropped, which is a trap for whoever adds that field later without
    # reading build_call_goal first. Reject it now, the same way seating_custom
    # is rejected outside custom seating, rather than accepting and discarding it.
    special_instructions = optional_text("special_instructions", 500)
    if mode is not Mode.RESERVATION and special_instructions:
        raise ValueError(
            "special_instructions is only supported for reservations; "
            f"{mode.value} has no way to pass it on to the restaurant"
        )

    # E29 (2026-08-22): missing entirely from this function -- the browser
    # form marks max_budget_eur as required, so this only surfaced through a
    # direct API POST that skips that client-side check. Without it,
    # max_budget_eur silently stayed None all the way to engine.build_call_goal,
    # which formats it as "{request.max_budget_eur:.2f}" and crashed with an
    # unhandled TypeError -- a 500, not the clean 400 every other missing
    # required field here already gets. Validated the same way as
    # first_name/last_name/requester_callback_number above: raise ValueError,
    # which every caller (this function's callers, /api/preview-goal, the
    # order-start route) already turns into a proper 400 response.
    max_budget_eur = as_float("max_budget_eur") if mode is not Mode.RESERVATION else None
    if mode is not Mode.RESERVATION and max_budget_eur is None:
        raise ValueError("max_budget_eur is required for delivery and pickup")

    return UserRequest(
        mode=mode,
        customer_name=customer_name,
        food_prompt=food_prompt,
        max_budget_eur=max_budget_eur,
        delivery_address=fields.get("delivery_address"),
        reservation_date=reservation_date,
        reservation_time=fields.get("reservation_time"),
        party_size=as_int("party_size"),
        seating=seating,
        pickup_time=fields.get("pickup_time") or "19:30",
        max_distance_km=as_float("max_distance_km"),
        day_of_week=day,
        time_of_request=fields.get("reservation_time") or time_override or current_clock(),
        concessions=concessions,
        order_chain=chain,
        first_name=first_name,
        last_name=last_name,
        requester_callback_number=requester_callback_number,
        seating_custom=seating_custom,
        special_instructions=special_instructions,
        earlier_hours=earlier_hours if mode is Mode.RESERVATION else 0,
        later_hours=later_hours if mode is Mode.RESERVATION else 0,
        earlier_minutes=earlier_minutes if mode is Mode.RESERVATION else 0,
        later_minutes=later_minutes if mode is Mode.RESERVATION else 0,
        max_booking_fee_eur=max_booking_fee_eur if mode is Mode.RESERVATION else 0.0,
    )


def rebuild_pool(
    city: str,
    lat: float,
    lon: float,
    radius_km: float,
    test_mode: bool = False,
) -> list[Restaurant]:
    """Build a candidate pool from its explicitly selected restaurant source."""
    return search_overpass_restaurants(
        lat=lat, lon=lon, radius_km=radius_km, test_mode=test_mode, city=city
    )


def localized_search_error(exc: RestaurantSearchError, lang: str, radius_km: float) -> str:
    """Return the same clear reason used by the HTML error panel."""
    if exc.code == "address_not_found":
        return t("search.error.address.body", lang)
    if exc.code == "no_restaurants":
        return t("search.error.none.body", lang, radius=f"{radius_km:g}")
    return t("search.error.service.body", lang)


def criteria_line(request: UserRequest, lang: str) -> str:
    """The one-line summary of what the table branch is actually testing."""
    parts = [
        f'{request.reservation_time or "?"}',
        t("candidates.seats", lang, n=request.party_size or 0),
    ]
    if request.seating is Seating.CUSTOM:
        parts.append(request.seating_custom or t("table.seating.custom", lang))
    elif request.seating is not Seating.ANY:
        parts.append(t(f"table.seating.{request.seating.value}", lang))
    if request.earlier_tolerance_minutes():
        parts.append(t(
            "table.authority.earlier", lang,
            minutes=request.earlier_tolerance_minutes(),
        ))
    if request.later_tolerance_minutes():
        parts.append(t(
            "table.authority.later", lang,
            minutes=request.later_tolerance_minutes(),
        ))
    if request.max_booking_fee_eur > 0:
        parts.append(t(
            "table.authority.fee", lang,
            fee=f"{request.max_booking_fee_eur:.2f}",
        ))
    return " · ".join(parts)


# --------------------------------------------------------------------------
# Step 2 — candidates
# --------------------------------------------------------------------------

@app.post("/api/search", response_class=HTMLResponse)
async def api_search(request: Request):
    form = await request.form()
    lang = lang_of(request)
    fields = {k: form.get(k) for k in form}
    branch = Branch(fields.get("branch") or "food")

    city = fields.get("city") or "Dorfstadt"
    postcode = fields.get("postcode") or ""
    radius_km = float(fields.get("radius_km") or 3.0)
    test_mode = restaurant_test_mode.active(request.cookies)
    transport = fields.get("transport") or "dry_run"

    if transport == "live" and fields.get("confirm_live") != "yes":
        return HTMLResponse(
            f'<div class="notice warn" style="margin-top:1rem;">{t("error.live.refused", lang)}</div>',
            status_code=400,
        )
    if transport == "live" and test_mode and not field_trial_active():
        return HTMLResponse(
            f'<div class="notice warn" style="margin-top:1rem;">{t("error.test_mode.live", lang)}</div>',
            status_code=400,
        )

    try:
        lat, lon = geocode_location(
            postcode, city, "Deutschland", test_mode=test_mode
        )
    except RestaurantSearchError as exc:
        return HTMLResponse(render_search_error(lang, exc.code, radius_km))

    try:
        pool = rebuild_pool(city, lat, lon, radius_km, test_mode=test_mode)
    except RestaurantSearchError as exc:
        return HTMLResponse(
            render_search_error(
                lang, exc.code, radius_km, lat=lat, lon=lon
            )
        )

    fields["concessions"] = form.getlist("concessions")
    try:
        user_request = build_user_request(
            fields,
            day_override=restaurant_test_mode.FIXTURE_DAY if test_mode else None,
            time_override=restaurant_test_mode.FIXTURE_TIME if test_mode else None,
        )
    except ValueError as exc:
        return HTMLResponse(
            f'<div class="notice warn">{html.escape(t("order.error.invalid", lang, detail=str(exc)))}</div>',
            status_code=400,
        )

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
        "first_name": user_request.first_name,
        "last_name": user_request.last_name,
        "requester_callback_number": user_request.requester_callback_number,
        "food_prompt": user_request.food_prompt,
        "order_chain_json": (
            order_chain_json(user_request.order_chain) if user_request.order_chain else None
        ),
        "delivery_address": user_request.delivery_address,
        "max_budget_eur": user_request.max_budget_eur,
        "pickup_time": user_request.pickup_time,
        "max_distance_km": user_request.max_distance_km,
        "reservation_date": user_request.reservation_date,
        "reservation_time": user_request.reservation_time,
        "party_size": user_request.party_size,
        "seating": user_request.seating.value,
        "seating_custom": user_request.seating_custom,
        "special_instructions": user_request.special_instructions,
        "earlier_hours": user_request.earlier_hours,
        "later_hours": user_request.later_hours,
        "earlier_minutes": user_request.earlier_minutes,
        "later_minutes": user_request.later_minutes,
        "max_booking_fee_eur": user_request.max_booking_fee_eur,
        "concessions": [c.key for c in user_request.concessions],
        "transport": transport,
        "confirm_live": "yes" if fields.get("confirm_live") == "yes" else None,
    }

    return HTMLResponse(render_candidate_step(
        lang=lang, branch=branch, ranked=ranked, skipped=skipped,
        lat=lat, lon=lon, radius_km=radius_km, form_state=form_state,
        source_count=len(pool), test_mode=test_mode,
    ))


@app.post("/api/preview-goal", response_class=JSONResponse)
async def api_preview_goal(request: Request):
    """The exact text that will leave the building — from the same function
    that builds it for real, never a copy of it written in JavaScript."""
    form = await request.form()
    fields = {k: form.get(k) for k in form}
    fields["concessions"] = form.getlist("concessions")
    lang = lang_of(request)
    test_mode = restaurant_test_mode.active(request.cookies)

    try:
        user_request = build_user_request(
            fields,
            day_override=restaurant_test_mode.FIXTURE_DAY if test_mode else None,
            time_override=restaurant_test_mode.FIXTURE_TIME if test_mode else None,
        )
        verify_content_safety(
            user_request.food_prompt,
            notes=" ".join(
                value for value in (
                    user_request.seating_custom, user_request.special_instructions
                ) if value
            ),
        )
    except SafetyError:
        return JSONResponse({"error": t("error.unsafe.content", lang)}, status_code=400)
    except (ValueError, KeyError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    city = fields.get("city") or "Dorfstadt"
    radius_km = float(fields.get("radius_km") or 3.0)
    try:
        lat, lon = geocode_location(
            fields.get("postcode") or "", city, "Deutschland", test_mode=test_mode
        )
        pool = rebuild_pool(city, lat, lon, radius_km, test_mode=test_mode)
    except RestaurantSearchError as exc:
        return JSONResponse(
            {"error": localized_search_error(exc, lang, radius_km)}, status_code=503
        )
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
    fields = {k: form.get(k) for k in form}
    fields["concessions"] = form.getlist("concessions")

    branch = Branch(fields.get("branch") or "food")
    city = fields.get("city") or "Dorfstadt"
    radius_km = float(fields.get("radius_km") or 3.0)
    test_mode = restaurant_test_mode.active(request.cookies)
    live_mode = fields.get("transport") == "live"

    if live_mode and fields.get("confirm_live") != "yes":
        return HTMLResponse(
            f'<div class="notice warn" style="margin-top:1rem;">{t("error.live.refused", lang)}</div>',
            status_code=400,
        )
    if live_mode and test_mode and not field_trial_active():
        return HTMLResponse(
            f'<div class="notice warn" style="margin-top:1rem;">{t("error.test_mode.live", lang)}</div>',
            status_code=400,
        )

    try:
        lat, lon = geocode_location(
            fields.get("postcode") or "", city, "Deutschland", test_mode=test_mode
        )
        pool = rebuild_pool(city, lat, lon, radius_km, test_mode=test_mode)
    except RestaurantSearchError as exc:
        return HTMLResponse(render_search_error(lang, exc.code, radius_km))

    try:
        user_request = build_user_request(
            fields,
            day_override=restaurant_test_mode.FIXTURE_DAY if test_mode else None,
            time_override=restaurant_test_mode.FIXTURE_TIME if test_mode else None,
        )
        verify_content_safety(
            user_request.food_prompt,
            notes=" ".join(
                value for value in (
                    user_request.seating_custom, user_request.special_instructions
                ) if value
            ),
        )
    except SafetyError:
        return HTMLResponse(
            f'<div class="notice warn" style="margin-top:1rem;">{t("error.unsafe.content", lang)}</div>'
        )
    except ValueError as exc:
        return HTMLResponse(
            f'<div class="notice warn" style="margin-top:1rem;">'
            f'{html.escape(t("order.error.invalid", lang, detail=str(exc)))}</div>',
            status_code=400,
        )

    by_id = {r.id: r for r in pool}

    # The order the user sees is the order we call. Browser fields are not an
    # authority boundary, though: a crafted POST must not revive a restaurant
    # that search pre-filtered as closed, incompatible, too far away, or too
    # small for the party.
    eligible_ids = {
        restaurant.id
        for restaurant, _score in filter_and_rank_restaurants(pool, user_request)
    }
    selected = set(form.getlist("selected_restaurants"))
    ordered_ids = [i for i in (fields.get("candidate_order") or "").split(",") if i]
    call_order = [
        by_id[i]
        for i in ordered_ids
        if i in eligible_ids and i in selected
    ]

    if not call_order:
        return HTMLResponse(
            f'<div class="notice warn" style="margin-top:1rem;">{t("candidates.none", lang)}</div>'
        )

    scenario = fields.get("scenario") or DEFAULT_SCENARIOS[user_request.mode]
    trial_number = None
    if live_mode:
        try:
            call_client = live_call_client()
            # Search results and fixtures carry strangers' numbers; a live
            # field trial rewires every candidate to the consenting test line.
            call_order, trial_number = field_trial.apply(call_order)
        except SafetyError as exc:
            return HTMLResponse(
                '<div class="notice warn" style="margin-top:1rem;">'
                f'<strong>{t("error.live.settings", lang)}</strong><br>{html.escape(str(exc))}</div>',
                status_code=400,
            )
    else:
        call_client = DryRunCallClient(scenario_name=scenario)
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
        dry_run=not live_mode,
        order_chain=(user_request.order_chain.to_dict() if user_request.order_chain else None),
    )
    if user_request.order_chain:
        save_tags(user_request.order_chain.all_tags())

    ACTIVE_ORDERS[order_id] = {
        "request": user_request,
        "candidates": call_order,
        "scenario": scenario,
        "branch": branch,
        "call_client": call_client,
        "live_mode": live_mode,
        "field_trial_number": trial_number,
        # Which browser session this cascade belongs to. An order id is an
        # identifier, not a permission: this dictionary lives in one process
        # that, hosted, several visitors share. See active_order().
        "session": huckepack_storage.current_session(),
    }

    return HTMLResponse(render_cascade_monitor(
        lang=lang,
        order_id=order_id,
        mode=user_request.mode,
        max_budget_eur=user_request.max_budget_eur,
        criteria_line=criteria_line(user_request, lang),
        concession_keys=[c.key for c in user_request.concessions],
        live_mode=live_mode,
    ))


def active_order(order_id: str) -> dict[str, Any] | None:
    """The running cascade with this id — if it belongs to this browser.

    In ``local`` nothing changes: one installation, one user. In a huckepack
    mode the process is shared by strangers, and an eight-character order id
    is not a password. A cascade is therefore handed back only to the session
    that started it; to anyone else the order simply does not exist.
    """
    order = ACTIVE_ORDERS.get(order_id)
    if order is None:
        return None
    if not current_mode().stores_in_browser:
        return order
    return order if order.get("session") == huckepack_storage.current_session() else None


def field_trial_active() -> bool:
    """Whether every live call is rewired to the consenting test number.

    Fixture restaurants may meet a live wire only under this override —
    their sample phone numbers belong to strangers. An invalid configured
    value counts as absent (fail-closed): the combination stays refused.
    """
    try:
        return field_trial.trial_phone() is not None
    except SafetyError:
        return False


def live_call_client() -> LiveCallClient:
    """The single seam where a live client is built.

    Whose key it uses depends on the server mode: the host's own credential in
    ``local`` and ``huckepack-gift``, the visitor's borrowed one in
    ``huckepack-only-host`` — where it lives for this request and is written
    nowhere. Keeping this in one function means there is exactly one place to
    read when asking "could this call be charged to the wrong account?".
    """
    return LiveCallClient(resolve_call_settings(), confirmed=True)


def sse(payload: dict[str, Any]) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


# engine.evaluate_result() (and its private check_* helpers) build these
# exact strings for storage, the CLI and the API -- all of which stay
# English on purpose; existing tests and the call_attempts column assert
# that English text. The cockpit is the one place a person without English
# reads the judgment live (field-trial finding 2026-08-22, E19: the German
# cockpit showed the raw English "Order was not placed" for a rejected Asia
# Imbiss call), so this maps the code's own hardcoded fallback reasons to a
# translation key for display only. Anything not in this table -- in
# particular struct.get("rejection_reason") when the call itself supplied
# one, or one of engine.py's rarer f-string guard messages (a booking-fee or
# authority-step mismatch, an unauthorised concession, a call that failed
# outright) -- is shown exactly as received: that text was authored by the
# call, or is a defensive edge case not worth guessing a translation for.
_STATIC_ENGINE_REASON_KEYS: dict[str, str] = {
    "Restaurant does not deliver to specified address": "cascade.reason.no_delivery",
    "Pickup not available at restaurant": "cascade.reason.no_pickup",
    "No table available for requested date and time": "cascade.reason.no_table",
    "Reservation was not confirmed": "cascade.reason.reservation_unconfirmed",
    "The custom seating preference was not confirmed": "cascade.reason.seating_unconfirmed",
    "Unclear price statement (vague or missing exact quote)": "cascade.reason.price_unclear",
    "Unclear price statement: total_price_eur missing": "cascade.reason.price_missing",
    "Order was not placed": "cascade.reason.order_not_placed",
    "Order wish chain did not resolve": "cascade.reason.chain_unresolved",
}


def localize_engine_reason(reason: str, lang: str) -> str:
    """Translate one of engine.py's own hardcoded rejection reasons."""
    key = _STATIC_ENGINE_REASON_KEYS.get(reason)
    return t(key, lang) if key else reason


def cascade_stream_label_and_reason(
    call_result: CallResult, rejection_reason: str | None, lang: str
) -> tuple[str, str]:
    """The (label, reason) shown on the live cockpit for one dialled attempt.

    Field-trial finding 2026-08-22 (E21): a call that never produced a
    usable conversation (busy, no answer, or a technically completed call
    with no evaluable structured result) was labelled "Abgelehnt"/"Declined"
    -- the same as a restaurant that explicitly declined a criterion -- and
    the raw internal reason ("Structured result is missing required fields:
    pickup_available, order_chain_results") leaked straight into the
    cockpit. This is display-only: the underlying (passed, rejection_reason)
    decision from evaluate_result() is unchanged, and the raw reason is
    still what gets persisted to call_attempts for the record.
    """
    category = classify_rejection(call_result, rejection_reason)
    if category == "not_reached":
        reason = rejection_reason or ""
        if reason.startswith("Structured result is missing required fields"):
            reason = t("cascade.reason.no_conversation", lang)
        return t("cascade.not_reached", lang), reason
    return t("cascade.rejected", lang), localize_engine_reason(rejection_reason or "", lang)


@app.get("/api/cascade-stream")
async def cascade_stream(request: Request, order_id: str = Query(...)):
    """Run the cascade and narrate it.

    The events are data, not markup: the client decides what a rejection looks
    like. That keeps the wire format testable without a browser.
    """
    lang = lang_of(request)
    order = active_order(order_id)

    if not order:
        async def gone():
            yield sse({"type": "status", "text": t("cascade.exhausted", lang)})
            yield sse({"type": "done"})
        return StreamingResponse(gone(), media_type="text/event-stream")

    user_request: UserRequest = order["request"]
    candidates: list[Restaurant] = order["candidates"]
    client = order["call_client"]
    live_mode = bool(order.get("live_mode"))
    engine = CascadeEngine(candidate_pool=candidates, call_client=client, preserve_order=True)

    async def event_generator():
        yield sse({"type": "status", "text": t("cascade.init", lang)})
        if order.get("field_trial_number"):
            yield sse({
                "type": "status",
                "text": t(
                    "cascade.field_trial", lang,
                    phone=mask_phone(order["field_trial_number"]),
                ),
            })
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
            if not live_mode:
                await asyncio.sleep(DRY_RUN_DIAL_SECONDS)

            if order_id in CANCELED_ORDERS:
                yield sse({"type": "canceled", "text": t("cascade.canceled", lang)})
                return

            try:
                call_args = {
                    "restaurant": restaurant,
                    "user_request": user_request,
                    "idempotency_key": generate_idempotency_key(
                        user_request.mode.value, restaurant.id, time.time()
                    ),
                }
                if live_mode:
                    call_result = await asyncio.to_thread(
                        client.execute_candidate_call, **call_args
                    )
                else:
                    call_result = client.execute_candidate_call(**call_args)
            except (CalleAPIError, RuntimeError, TimeoutError, SafetyError) as exc:
                yield sse({
                    "type": "error",
                    "text": f'{t("error.live.transport", lang)} {exc}',
                })
                return
            engine.redact_requester_callback(
                call_result, user_request.requester_callback_number
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
                if not live_mode:
                    await asyncio.sleep(DRY_RUN_TURN_SECONDS)

            passed, rejection_reason = engine.evaluate_result(user_request, call_result)

            # The order receipt lives here: every dialled attempt is stored
            # with its masked transcript — the accepted one proves the order,
            # the rejected ones explain the cascade (user decision 2026-08-11).
            record_call_attempt(
                order_id=order_id,
                restaurant_id=restaurant.id,
                restaurant_name=restaurant.name,
                run_id=call_result.run_id,
                status=call_result.status.value,
                passed=passed,
                rejection_reason=rejection_reason,
                post_summary=call_result.post_summary,
                transcript=mask_phones_in_text(call_result.raw_transcript_text or ""),
                live=live_mode,
            )

            if not passed:
                label, display_reason = cascade_stream_label_and_reason(
                    call_result, rejection_reason, lang
                )
                yield sse({
                    "type": "rejected",
                    "id": restaurant.id,
                    "label": label,
                    "reason": display_reason,
                })
                await asyncio.sleep(0.4)
                continue

            concession_used = call_result.structured_result.get("tier_applied") or None
            chain_evaluation = (
                evaluate_order_chain(user_request.order_chain, call_result.structured_result)
                if user_request.order_chain else None
            )
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
                    order_chain=user_request.order_chain,
                    chain_evaluation=chain_evaluation,
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
    """Stop before the next number is dialled — your own cascade, not a stranger's."""
    lang = lang_of(request)
    if active_order(order_id) is None:
        return HTMLResponse(f'<span class="mono">{t("history.empty", lang)}</span>')
    CANCELED_ORDERS.add(order_id)
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
    order = active_order(order_id) or {}
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
    return HTMLResponse(
        f'<span class="mono">{t("result.saved", lang)}</span>'
        + huckepack_web.receipt_script_tag(
            build_receipt_payload(
                order_id=order_id,
                mode=user_request.mode.value,
                restaurant=restaurant,
                structured=structured,
                call_result=call_result,
                customer_name=user_request.customer_name,
            )
        )
    )


def build_receipt_payload(
    *,
    order_id: str,
    mode: str,
    restaurant: Restaurant,
    structured: dict[str, Any],
    call_result: Any,
    customer_name: str,
) -> dict[str, Any]:
    """What the browser needs to write a receipt file — with numbers masked.

    Masked here rather than in the browser, so a payload that ends up in a
    developer console or a page cache carries no dialable number either. The
    transcript goes through the same masking as the stored one.
    """
    return {
        "kind": "call-receipt",
        "app": "hungrycall",
        "order_id": order_id,
        "mode": mode,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "business": restaurant.name,
        "business_phone_masked": mask_phone(restaurant.phone),
        "callback_number_masked": mask_phone(
            structured.get("callback_number") or restaurant.phone
        ),
        "customer_name": customer_name,
        "total_price_eur": structured.get("total_price_eur"),
        "eta_minutes": structured.get("eta_minutes") or structured.get("prep_time_minutes"),
        "summary": call_result.post_summary,
        "transcript": mask_phones_in_text(call_result.raw_transcript_text or ""),
        "third_party_notice": (
            "This transcript contains statements by the person who was called."
        ),
    }


@app.get("/api/order-attempts", response_class=JSONResponse)
async def api_get_order_attempts(request: Request, order_id: str = Query(...)):
    """Dialled attempts of one order, masked transcripts included.

    Same session rule as active_order(): in hosted modes an order id is an
    identifier, not a permission — foreign sessions see an empty list.
    """
    order = ACTIVE_ORDERS.get(order_id)
    if (
        order is not None
        and current_mode().stores_in_browser
        and order.get("session") != huckepack_storage.current_session()
    ):
        return []
    return list_call_attempts(order_id)


@app.get("/api/saved-results", response_class=JSONResponse)
async def api_get_saved_results():
    return list_saved_results()


@app.post("/api/order-templates", response_class=JSONResponse)
async def api_save_order_template(
    name: str = Form(...),
    order_chain_json_value: str = Form(..., alias="order_chain_json"),
):
    try:
        chain = parse_order_chain(order_chain_json_value)
        if chain is None:
            raise ValueError("order chain is required")
        saved = save_order_template(name, chain.to_dict())
        save_tags(chain.all_tags())
        return JSONResponse(saved)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.get("/api/order-templates", response_class=JSONResponse)
async def api_get_order_templates():
    return list_order_templates()


def main():
    """CLI entrypoint to run the HungryCall web server."""
    import uvicorn
    print("Starting HungryCall on http://127.0.0.1:8000 ...")
    uvicorn.run("hungrycall.web:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
