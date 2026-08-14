"""Fixtures and mock responses for dry-run execution without network or account."""

from typing import Any

from hungrycall.models import (
    CallStatus,
    OpeningHours,
    Restaurant,
    UserRequest,
)

ALL_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# The one default candidate pool. location.py serves copies of this list rather
# than keeping a second, slowly diverging one.
SAMPLE_RESTAURANTS: list[Restaurant] = [
    Restaurant(
        id="rest_burger_house",
        name="Burger House Dorfstadt",
        phone="+441632960000",
        cuisines=["Burger", "American", "Fast Food"],
        opening_hours=OpeningHours(days=ALL_WEEK, open_time="11:00", close_time="23:00"),
        is_favorite=False,
        supports_delivery=True,
        supports_pickup=True,
        supports_reservation=True,
        address="Dorfstraße 5, 12345 Dorfstadt",
        email="info@burgerhouse.example",
        lat=52.5220,
        lon=13.4080,
        has_outdoor_seating=False,
        max_party_size=6,
    ),
    Restaurant(
        id="rest_trattoria_luigi",
        name="Trattoria Bella Luigi",
        phone="+441632960001",
        cuisines=["Italian", "Pizza", "Pasta"],
        opening_hours=OpeningHours(days=ALL_WEEK, open_time="12:00", close_time="22:00"),
        is_favorite=True,  # Favourite Italian restaurant
        supports_delivery=True,
        supports_pickup=True,
        supports_reservation=True,
        address="Marktplatz 1, 12345 Dorfstadt",
        email="luigi@trattoriabella.example",
        lat=52.5180,
        lon=13.4020,
        has_outdoor_seating=True,
        max_party_size=10,
    ),
    Restaurant(
        id="rest_asian_wok",
        name="Asia Wok Express",
        phone="+441632960002",
        cuisines=["Asian", "Chinese", "Noodles"],
        opening_hours=OpeningHours(
            days=["Wed", "Thu", "Fri", "Sat", "Sun"], open_time="16:00", close_time="22:00"
        ),
        is_favorite=False,
        supports_delivery=True,
        supports_pickup=True,
        supports_reservation=False,
        address="Bahnhofstraße 12, 12345 Dorfstadt",
        lat=52.5240,
        lon=13.3980,
        has_outdoor_seating=False,
        max_party_size=4,
    ),
    Restaurant(
        id="rest_gasthaus_linde",
        name="Gasthaus Zur Linde",
        phone="+441632960004",
        cuisines=["German", "Regional", "Beer Garden"],
        opening_hours=OpeningHours(
            days=["Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], open_time="11:30", close_time="23:00"
        ),
        is_favorite=False,
        supports_delivery=False,  # village pub: you come to them
        supports_pickup=True,
        supports_reservation=True,
        address="Lindenallee 3, 12345 Dorfstadt",
        lat=52.5310,
        lon=13.4210,
        has_outdoor_seating=True,
        max_party_size=24,
    ),
    Restaurant(
        id="rest_sushi_kudo",
        name="Sushi Kudo",
        phone="+441632960005",
        cuisines=["Japanese", "Sushi", "Ramen"],
        opening_hours=OpeningHours(
            days=["Tue", "Wed", "Thu", "Fri", "Sat"], open_time="17:00", close_time="22:30"
        ),
        is_favorite=False,
        supports_delivery=True,
        supports_pickup=True,
        supports_reservation=True,
        address="Poststraße 21, 12345 Dorfstadt",
        lat=52.5090,
        lon=13.3870,
        has_outdoor_seating=False,
        max_party_size=8,
    ),
    Restaurant(
        id="rest_closed_diner",
        name="Late Night Snack Shack",
        phone="+441632960003",
        cuisines=["Burger", "Snack"],
        opening_hours=OpeningHours(days=["Fri", "Sat"], open_time="22:00", close_time="04:00"),
        is_favorite=False,
        supports_delivery=True,
        supports_pickup=True,
        supports_reservation=False,
        address="Industriestraße 8, 12345 Dorfstadt",
        lat=52.5150,
        lon=13.4120,
        has_outdoor_seating=False,
        max_party_size=4,
    ),
]


def format_transcript_text(transcript_list: list[dict[str, str]]) -> str:
    """Format transcript list into standard CALL-E string format: [mm:ss] SPRECHER: Text"""
    lines = []
    for turn in transcript_list:
        ts = turn.get("ts", "00:00")
        if len(ts) == 8 and ts.startswith("00:"):
            ts_short = ts[3:]  # '00:00:05' -> '00:05'
        else:
            ts_short = ts
        speaker = turn.get("speaker", "BOT")
        if speaker in ["Agent", "BOT"]:
            speaker_norm = "BOT"
        elif speaker in ["Restaurant", "USER", "Callee"]:
            speaker_norm = "USER"
        else:
            speaker_norm = speaker
        lines.append(f"[{ts_short}] {speaker_norm}: {turn.get('text', '')}")
    return "\n".join(lines)


def deduplicate_activity(activity_events: list[str]) -> list[str]:
    """
    Deduplicate real-time STT streaming drafts in activity log.
    Speech recognition initially emits raw draft ('Callee said: hallo')
    followed immediately by corrected version ('Callee said: Hallo.').
    This helper filters out intermediate drafts when followed by a refined version.
    """
    if not activity_events:
        return []

    deduped = []
    for i, event in enumerate(activity_events):
        if "Callee said:" in event and i < len(activity_events) - 1:
            next_event = activity_events[i + 1]
            if "Callee said:" in next_event:
                curr_text = event.split("Callee said:", 1)[1].strip()
                next_text = next_event.split("Callee said:", 1)[1].strip()
                if next_text.lower().startswith(curr_text.lower()) or curr_text.lower() in next_text.lower():
                    continue
        deduped.append(event)
    return deduped


def render_fixture_data(mock_entry: dict[str, Any], req: UserRequest, restaurant: Restaurant) -> dict[str, Any]:
    """Interpolate actual user request inputs into fixture data templates."""
    fmt_kwargs = {
        "customer_name": req.customer_name,
        "delivery_address": req.delivery_address or "Specified Address",
        "food_prompt": req.food_prompt,
        "max_budget_eur": f"{req.max_budget_eur:.2f}" if req.max_budget_eur is not None else "35.00",
        "reservation_date": req.reservation_date or "2026-08-05",
        "reservation_time": req.reservation_time or "19:00",
        "party_size": str(req.party_size) if req.party_size is not None else "4",
        "pickup_time": req.pickup_time or "19:30",
        "seating": req.seating.value,
        "restaurant_name": restaurant.name,
        "restaurant_address": restaurant.address,
    }

    def interpolate(value: Any) -> Any:
        if isinstance(value, str):
            for k, v in fmt_kwargs.items():
                value = value.replace(f"{{{k}}}", str(v))
        return value

    # Render post_summary
    post_summary = interpolate(mock_entry.get("post_summary", ""))

    # Render structured_result. Without this a rejection_reason reaches the
    # screen with a literal "{max_budget_eur}" in it. Copied, not mutated in
    # place: SCENARIO_FIXTURES is module-level and shared across calls.
    structured_result = {
        key: interpolate(value)
        for key, value in mock_entry.get("structured_result", {}).items()
    }

    # Render transcript
    raw_transcript = mock_entry.get("transcript", [])
    rendered_transcript = []
    for turn in raw_transcript:
        turn_copy = dict(turn)
        text = turn_copy.get("text", "")
        for k, v in fmt_kwargs.items():
            text = text.replace(f"{{{k}}}", str(v))
        turn_copy["text"] = text
        rendered_transcript.append(turn_copy)

    # Render activity
    raw_activity = mock_entry.get("activity", [])
    rendered_activity = []
    for act in raw_activity:
        act_text = act
        for k, v in fmt_kwargs.items():
            act_text = act_text.replace(f"{{{k}}}", str(v))
        rendered_activity.append(act_text)

    transcript_text = format_transcript_text(rendered_transcript)

    return {
        "status": mock_entry.get("status", CallStatus.COMPLETED),
        "structured_result": structured_result,
        "post_summary": post_summary,
        "transcript": rendered_transcript,
        "activity": rendered_activity,
        "raw_transcript_text": transcript_text
    }


# Mock responses mapped by scenario preset name and restaurant ID
SCENARIO_FIXTURES: dict[str, dict[str, Any]] = {
    # Scenario 1: Immediate success
    "success_direct": {
        "rest_burger_house": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "delivers_to_address": True,
                "price_known": True,
                "total_price_eur": 28.50,
                "eta_minutes": 35,
                "order_placed": True,
                "callback_number": "+441632960000",
                "rejection_reason": None
            },
            "post_summary": "Order placed successfully. Total: 28.50 EUR, ETA: 35 minutes.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, I am an automated assistant calling on behalf of {customer_name}. Do you deliver to {delivery_address}?"},
                {"ts": "00:00:10", "speaker": "USER", "text": "Yes, we deliver to {delivery_address}."},
                {"ts": "00:00:15", "speaker": "BOT", "text": "Great! What is the exact total price including delivery fee for {food_prompt}?"},
                {"ts": "00:00:22", "speaker": "USER", "text": "The total end price at your door is exactly 28 Euros and 50 Cents."},
                {"ts": "00:00:28", "speaker": "BOT", "text": "Perfect, that is within our {max_budget_eur} Euro limit. Please place the order. How long will it take?"},
                {"ts": "00:00:35", "speaker": "USER", "text": "Order is confirmed! Delivery will take about 35 minutes."},
                {"ts": "00:00:40", "speaker": "BOT", "text": "Thank you very much. Goodbye!"}
            ],
            "activity": [
                "17:37:05.100 | Bot initialized.",
                "17:37:44.200 | Call is ringing (~40s setup latency).",
                "17:37:49.500 | Call connected.",
                "17:37:50.700 | Bot is speaking: Hello, I am an automated assistant calling on behalf of {customer_name}. Do you deliver to {delivery_address}?",
                "17:37:51.500 | Callee said: ja",
                "17:37:52.200 | Callee said: Ja, wir liefern nach {delivery_address}.",
                "17:38:15.800 | Bot is speaking: Great! What is the exact total price including delivery fee for {food_prompt}?",
                "17:38:21.300 | Callee said: 28.50 Euro.",
                "17:38:40.100 | Call ended; syncing final Calling result."
            ]
        }
    },

    # Scenario 2: First candidate vague price, second candidate succeeds
    "vague_price_cascade": {
        "rest_burger_house": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "delivers_to_address": True,
                "price_known": False,  # Vague price!
                "total_price_eur": 30.0,
                "eta_minutes": 40,
                "order_placed": False,
                "callback_number": "+441632960000",
                "rejection_reason": "Unclear price statement: Restaurant said 'about 30 Euro depending on driver'"
            },
            "post_summary": "Declined order due to unconfirmed vague price quote.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. What is the total price for {food_prompt}?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "Well, it's so roughly around 30 Euros, depends a bit on the delivery driver fee today."},
                {"ts": "00:00:20", "speaker": "BOT", "text": "I am sorry, I need an exact total price to proceed. Since it is unconfirmed, I cannot place the order. Have a nice evening."}
            ],
            "activity": [
                "17:37:05.100 | Bot initialized.",
                "17:37:44.200 | Call is ringing (~40s setup latency).",
                "17:37:49.500 | Call connected.",
                "17:37:50.700 | Bot is speaking: Hello, calling on behalf of {customer_name}. What is the total price for {food_prompt}?",
                "17:37:51.500 | Callee said: ca 30 euro",
                "17:37:52.200 | Callee said: Well, it's so roughly around 30 Euros, depends a bit on the delivery driver fee today.",
                "17:38:15.800 | Bot is speaking: I am sorry, I need an exact total price to proceed.",
                "17:38:20.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_trattoria_luigi": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "delivers_to_address": True,
                "price_known": True,
                "total_price_eur": 29.00,
                "eta_minutes": 45,
                "order_placed": True,
                "callback_number": "+441632960001",
                "rejection_reason": None
            },
            "post_summary": "Order placed successfully at Trattoria Bella Luigi. Total 29.00 EUR.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. Can you deliver to {delivery_address}?"},
                {"ts": "00:00:10", "speaker": "USER", "text": "Yes, we deliver there. The total price is exactly 29.00 Euros."},
                {"ts": "00:00:18", "speaker": "BOT", "text": "29.00 EUR is within the {max_budget_eur} EUR limit. Please place the order for {food_prompt}."},
                {"ts": "00:00:25", "speaker": "USER", "text": "Order received! Delivery in 45 minutes."}
            ],
            "activity": [
                "17:38:30.100 | Bot initialized.",
                "17:39:10.200 | Call is ringing (~40s setup latency).",
                "17:39:15.500 | Call connected.",
                "17:39:16.700 | Bot is speaking: Hello, calling on behalf of {customer_name}. Can you deliver to {delivery_address}?",
                "17:39:18.200 | Callee said: Ja, liefern wir.",
                "17:39:25.800 | Call ended; syncing final Calling result."
            ]
        }
    },

    # Scenario 3: First candidate exceeds max budget, second candidate succeeds
    "budget_exceeded_cascade": {
        "rest_burger_house": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "delivers_to_address": True,
                "price_known": True,
                "total_price_eur": 42.00,  # Exceeds limit!
                "eta_minutes": 30,
                "order_placed": False,
                "callback_number": "+441632960000",
                "rejection_reason": "Total price 42.00 EUR exceeds budget limit of {max_budget_eur} EUR"
            },
            "post_summary": "Declined order: total 42.00 EUR exceeds limit of {max_budget_eur} EUR.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. What is the total price for delivery of {food_prompt} to {delivery_address}?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "With delivery charge and minimum order, the total is exactly 42 Euros."},
                {"ts": "00:00:20", "speaker": "BOT", "text": "That exceeds our maximum budget limit of {max_budget_eur} Euros. I must politely decline. Goodbye!"}
            ],
            "activity": [
                "17:37:05.100 | Bot initialized.",
                "17:37:44.200 | Call is ringing (~40s setup latency).",
                "17:37:49.500 | Call connected.",
                "17:37:50.700 | Bot is speaking: Hello, calling on behalf of {customer_name}. What is the total price for delivery of {food_prompt}?",
                "17:37:52.200 | Callee said: 42 Euro.",
                "17:38:00.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_trattoria_luigi": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "delivers_to_address": True,
                "price_known": True,
                "total_price_eur": 31.50,
                "eta_minutes": 40,
                "order_placed": True,
                "callback_number": "+441632960001",
                "rejection_reason": None
            },
            "post_summary": "Order placed successfully at Trattoria Bella Luigi. Total 31.50 EUR.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. Can you deliver {food_prompt} to {delivery_address} for 31.50 EUR total?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "Yes, total is 31.50 Euros. Order placed!"}
            ],
            "activity": [
                "17:38:10.100 | Bot initialized.",
                "17:38:50.200 | Call is ringing (~40s setup latency).",
                "17:38:55.500 | Call connected.",
                "17:38:56.700 | Bot is speaking: Hello, calling on behalf of {customer_name}.",
                "17:39:02.200 | Callee said: Ja, geht klar.",
                "17:39:10.100 | Call ended; syncing final Calling result."
            ]
        }
    },

    # Scenario 4: Table reservation cascade
    "reservation_cascade": {
        "rest_trattoria_luigi": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "table_available": True,
                "reservation_confirmed": True,
                "reservation_date_confirmed": "{reservation_date}",
                "reservation_time_confirmed": "{reservation_time}",
                "seating_preference_met": True,
                "booking_fee_eur": 0,
                "authority_steps_applied": [],
                "callback_number": "+441632960001",
                "rejection_reason": None
            },
            "post_summary": "Table reserved for {party_size} people on {reservation_date} at {reservation_time}.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. Do you have a table for {party_size} people on {reservation_date} at {reservation_time}?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "Yes, we have a table available at {reservation_time}."},
                {"ts": "00:00:18", "speaker": "BOT", "text": "Please reserve it under the name {customer_name}. What is your callback number in case we need to cancel?"},
                {"ts": "00:00:25", "speaker": "USER", "text": "Reserved! Our callback number is +44 7700 900001. See you then!"}
            ],
            "activity": [
                "17:37:05.100 | Bot initialized.",
                "17:37:44.200 | Call is ringing (~40s setup latency).",
                "17:37:49.500 | Call connected.",
                "17:37:50.700 | Bot is speaking: Hello, calling on behalf of {customer_name}. Do you have a table for {party_size} people?",
                "17:37:52.200 | Callee said: Ja, haben wir.",
                "17:38:00.100 | Call ended; syncing final Calling result."
            ]
        }
    },

    # Scenario 5: Pickup cascade
    "pickup_cascade": {
        "rest_burger_house": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "pickup_available": True,
                "price_known": True,
                "total_price_eur": 22.00,
                "prep_time_minutes": 20,
                "order_placed": True,
                "callback_number": "+441632960000",
                "rejection_reason": None
            },
            "post_summary": "Pickup order placed. Total 22.00 EUR, ready in 20 minutes.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. Can we place a pickup order for {food_prompt}?"},
                {"ts": "00:00:10", "speaker": "USER", "text": "Yes, pickup is available. Total price is 22 Euros."},
                {"ts": "00:00:16", "speaker": "BOT", "text": "22 Euros is within our {max_budget_eur} Euro limit. Please place the order. When will it be ready?"},
                {"ts": "00:00:22", "speaker": "USER", "text": "It will be ready in 20 minutes."}
            ],
            "activity": [
                "17:37:05.100 | Bot initialized.",
                "17:37:44.200 | Call is ringing (~40s setup latency).",
                "17:37:49.500 | Call connected.",
                "17:37:50.700 | Bot is speaking: Hello, calling on behalf of {customer_name}.",
                "17:37:52.200 | Callee said: Ja, in 20 Minuten fertig.",
                "17:38:00.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_trattoria_luigi": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "pickup_available": True,
                "price_known": False,
                "total_price_eur": 24.0,
                "prep_time_minutes": 25,
                "order_placed": False,
                "callback_number": "+441632960001",
                "rejection_reason": "Unclear price: 'somewhere around 24, depends on the toppings'"
            },
            "post_summary": "Declined: no exact total was given, so nothing was ordered.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. Pickup order for {food_prompt} — what is the exact total?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "Somewhere around 24 Euros, depends a bit on the toppings."},
                {"ts": "00:00:19", "speaker": "BOT", "text": "I need an exact total to order. Thank you anyway, goodbye."}
            ],
            "activity": [
                "17:36:05.100 | Bot initialized.",
                "17:36:45.200 | Call connected.",
                "17:36:52.200 | Callee said: So um die 24, kommt auf den Belag an.",
                "17:37:00.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_gasthaus_linde": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "pickup_available": True,
                "price_known": True,
                "total_price_eur": 21.40,
                "prep_time_minutes": 25,
                "order_placed": True,
                "callback_number": "+441632960004",
                "rejection_reason": None
            },
            "post_summary": "Pickup order placed at Gasthaus Zur Linde. Total 21.40 EUR, ready at {pickup_time}.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. Can we collect {food_prompt} at {pickup_time}?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "Yes. That comes to 21 Euros 40, ready in 25 minutes."},
                {"ts": "00:00:20", "speaker": "BOT", "text": "21.40 is within our {max_budget_eur} Euro limit. Please prepare it for {customer_name}."}
            ],
            "activity": [
                "17:38:10.100 | Bot initialized.",
                "17:38:50.200 | Call connected.",
                "17:38:58.200 | Callee said: 21 Euro 40, in 25 Minuten.",
                "17:39:10.100 | Call ended; syncing final Calling result."
            ]
        }
    },

    # Scenario 6: Reproducible 30-Second Core Jury Demo
    # Demonstrates: Budget Rejection -> Vague Price Rejection -> Direct Success -> Early Exit
    "jury_30s_demo": {
        "rest_burger_house": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "delivers_to_address": True,
                "price_known": True,
                "total_price_eur": 42.00,
                "eta_minutes": 30,
                "order_placed": False,
                "callback_number": "+441632960000",
                "rejection_reason": "Total price 42.00 EUR exceeds maximum budget limit of {max_budget_eur} EUR"
            },
            "post_summary": "Declined order: total price 42.00 EUR exceeds doorstep budget limit of {max_budget_eur} EUR.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. What is the total price for delivery of {food_prompt} to {delivery_address}?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "With delivery charge and minimum order, the total is exactly 42 Euros."},
                {"ts": "00:00:20", "speaker": "BOT", "text": "That exceeds our maximum budget limit of {max_budget_eur} Euros. I must politely decline. Goodbye!"}
            ],
            "activity": [
                "17:37:05.100 | Bot initialized.",
                "17:37:44.200 | Call ringing (~40s setup latency).",
                "17:37:49.500 | Call connected.",
                "17:37:50.700 | Bot is speaking: Hello, calling on behalf of {customer_name}. What is the total price for delivery of {food_prompt}?",
                "17:37:52.200 | Callee said: 42 Euro.",
                "17:38:00.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_trattoria_luigi": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "delivers_to_address": True,
                "price_known": False,
                "total_price_eur": 30.00,
                "eta_minutes": 40,
                "order_placed": False,
                "callback_number": "+441632960001",
                "rejection_reason": "Unclear price statement: Restaurant stated 'roughly around 30 Euros depending on driver'"
            },
            "post_summary": "Declined order due to unconfirmed vague price quote.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. What is the total price for delivery of {food_prompt}?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "Roughly around 30 Euros, depends on the driver fee today."},
                {"ts": "00:00:20", "speaker": "BOT", "text": "I need an exact total price to proceed. Since it is unconfirmed, I cannot place the order. Goodbye!"}
            ],
            "activity": [
                "17:38:10.100 | Bot initialized.",
                "17:38:49.200 | Call ringing (~40s setup latency).",
                "17:38:54.500 | Call connected.",
                "17:38:55.700 | Bot is speaking: Hello, calling on behalf of {customer_name}. What is the total price for delivery of {food_prompt}?",
                "17:38:57.200 | Callee said: Roughly 30 Euro.",
                "17:39:05.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_asian_wok": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "delivers_to_address": True,
                "price_known": True,
                "total_price_eur": 28.50,
                "eta_minutes": 35,
                "order_placed": True,
                "callback_number": "+441632960002",
                "rejection_reason": None
            },
            "post_summary": "Order placed successfully at Asia Wok Express. Total 28.50 EUR, ETA 35 minutes.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. Do you deliver to {delivery_address}?"},
                {"ts": "00:00:10", "speaker": "USER", "text": "Yes, we deliver to {delivery_address}."},
                {"ts": "00:00:15", "speaker": "BOT", "text": "What is the exact total price for {food_prompt}?"},
                {"ts": "00:00:22", "speaker": "USER", "text": "The exact total price at your door is 28.50 Euros."},
                {"ts": "00:00:28", "speaker": "BOT", "text": "28.50 EUR is within our {max_budget_eur} EUR limit. Please confirm the order."},
                {"ts": "00:00:35", "speaker": "USER", "text": "Order confirmed! Delivery will take 35 minutes."},
                {"ts": "00:00:40", "speaker": "BOT", "text": "Thank you. Callback at +44 7700 900002."}
            ],
            "activity": [
                "17:39:15.100 | Bot initialized.",
                "17:39:54.200 | Call ringing (~40s setup latency).",
                "17:39:59.500 | Call connected.",
                "17:40:00.700 | Bot is speaking: Hello, calling on behalf of {customer_name}. Do you deliver to {delivery_address}?",
                "17:40:02.200 | Callee said: Ja, 28.50 Euro.",
                "17:40:20.100 | Call ended; syncing final Calling result."
            ]
        }
    },

    # Scenario 7: Table branch cascade — same mechanics, different criteria.
    # Nothing here is about money: what decides is the clock, the party size and
    # where people sit. This is the evidence for MUSTER.md.
    "table_cascade": {
        "rest_trattoria_luigi": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "table_available": False,
                "reservation_confirmed": False,
                "reservation_date_confirmed": "{reservation_date}",
                "reservation_time_confirmed": "{reservation_time}",
                "seating_preference_met": False,
                "booking_fee_eur": 0,
                "authority_steps_applied": [],
                "callback_number": "+441632960001",
                "rejection_reason": "Fully booked from 18:30 on {reservation_date}"
            },
            "post_summary": "No table free at {reservation_time}. Ended the call politely.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, I am an automated assistant calling on behalf of {customer_name}. Do you have a table for {party_size} people on {reservation_date} at {reservation_time}?"},
                {"ts": "00:00:13", "speaker": "USER", "text": "I am sorry, we are fully booked from half past six that evening."},
                {"ts": "00:00:18", "speaker": "BOT", "text": "Thank you for checking. Have a good evening!"}
            ],
            "activity": [
                "19:02:05.100 | Bot initialized.",
                "19:02:44.200 | Call ringing (~40s setup latency).",
                "19:02:49.500 | Call connected.",
                "19:02:50.700 | Bot is speaking: Do you have a table for {party_size} people at {reservation_time}?",
                "19:02:57.200 | Callee said: Leider ausgebucht ab halb sieben.",
                "19:03:04.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_gasthaus_linde": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "table_available": True,
                "reservation_confirmed": True,
                "reservation_date_confirmed": "{reservation_date}",
                "reservation_time_confirmed": "{reservation_time}",
                "seating_confirmed": "outdoor",
                "seating_preference_met": True,
                "booking_fee_eur": 0,
                "authority_steps_applied": [],
                "callback_number": "+441632960004",
                "rejection_reason": None
            },
            "post_summary": "Table for {party_size} reserved in the beer garden at {reservation_time}, under {customer_name}.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. A table for {party_size} people on {reservation_date} at {reservation_time}, outside if possible?"},
                {"ts": "00:00:14", "speaker": "USER", "text": "The beer garden is open, yes. Table for {party_size} at {reservation_time}, that works."},
                {"ts": "00:00:20", "speaker": "BOT", "text": "Please reserve it under {customer_name}. What number can we call to cancel?"},
                {"ts": "00:00:28", "speaker": "USER", "text": "Reserved. Our number is 07700 900004. See you then!"}
            ],
            "activity": [
                "19:03:30.100 | Bot initialized.",
                "19:04:10.200 | Call ringing (~40s setup latency).",
                "19:04:15.500 | Call connected.",
                "19:04:16.700 | Bot is speaking: A table for {party_size} people at {reservation_time}, outside if possible?",
                "19:04:24.200 | Callee said: Biergarten ist offen, passt.",
                "19:04:38.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_burger_house": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "table_available": True,
                "reservation_confirmed": True,
                "reservation_date_confirmed": "{reservation_date}",
                "reservation_time_confirmed": "{reservation_time}",
                "seating_confirmed": "indoor",
                "seating_preference_met": True,
                "booking_fee_eur": 0,
                "authority_steps_applied": [],
                "callback_number": "+441632960000",
                "rejection_reason": None
            },
            "post_summary": "Indoor table for {party_size} reserved at {reservation_time} under {customer_name}.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. A table for {party_size} at {reservation_time}?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "Inside we have space, yes. We have no terrace."},
                {"ts": "00:00:19", "speaker": "USER", "text": "Booked under {customer_name}."}
            ],
            "activity": [
                "19:05:00.100 | Bot initialized.",
                "19:05:40.200 | Call ringing (~40s setup latency).",
                "19:05:45.500 | Call connected.",
                "19:05:52.200 | Callee said: Drinnen ja, Terrasse haben wir nicht.",
                "19:06:02.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_sushi_kudo": {
            "status": CallStatus.NO_ANSWER,
            "structured_result": {
                "table_available": False,
                "reservation_confirmed": False,
                "reservation_date_confirmed": "{reservation_date}",
                "reservation_time_confirmed": "{reservation_time}",
                "seating_preference_met": False,
                "booking_fee_eur": 0,
                "authority_steps_applied": [],
                "rejection_reason": "Nobody picked up after 6 rings"
            },
            "post_summary": "No answer. Moving on without a second attempt.",
            "transcript": [],
            "activity": [
                "19:06:20.100 | Bot initialized.",
                "19:07:00.200 | Call ringing (~40s setup latency).",
                "19:07:35.100 | No answer; call ended."
            ]
        }
    },

    # Scenario 8: Table branch with a granted concession (MUSTER.md tiers).
    # The engine only accepts this if the user actually authorised 'indoor_ok'.
    "table_concession_cascade": {
        "rest_trattoria_luigi": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "table_available": False,
                "reservation_confirmed": False,
                "reservation_date_confirmed": "{reservation_date}",
                "reservation_time_confirmed": "{reservation_time}",
                "seating_preference_met": False,
                "booking_fee_eur": 0,
                "authority_steps_applied": [],
                "callback_number": "+441632960001",
                "rejection_reason": "Fully booked on {reservation_date}"
            },
            "post_summary": "No table free at {reservation_time}. Ended the call politely.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. A table for {party_size} on {reservation_date} at {reservation_time}?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "Nothing free that evening, sorry."}
            ],
            "activity": [
                "19:02:05.100 | Bot initialized.",
                "19:02:45.200 | Call connected.",
                "19:02:52.200 | Callee said: Nichts frei an dem Abend.",
                "19:03:00.100 | Call ended; syncing final Calling result."
            ]
        },
        "rest_gasthaus_linde": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "table_available": True,
                "reservation_confirmed": True,
                "reservation_date_confirmed": "{reservation_date}",
                "reservation_time_confirmed": "{reservation_time}",
                "seating_confirmed": "indoor",
                "seating_preference_met": False,
                "booking_fee_eur": 0,
                "authority_steps_applied": [],
                "tier_applied": "indoor_ok",
                "callback_number": "+441632960004",
                "rejection_reason": None
            },
            "post_summary": "Beer garden booked out; fell back to the granted concession and took an indoor table for {party_size} at {reservation_time}.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. A table for {party_size} at {reservation_time}, outside if possible?"},
                {"ts": "00:00:13", "speaker": "USER", "text": "The beer garden is taken by a birthday party. Inside I could do it."},
                {"ts": "00:00:21", "speaker": "BOT", "text": "Inside is acceptable to us. Please book it under {customer_name}."},
                {"ts": "00:00:29", "speaker": "USER", "text": "Done, inside for {party_size} at {reservation_time}."}
            ],
            "activity": [
                "19:03:30.100 | Bot initialized.",
                "19:04:12.500 | Call connected.",
                "19:04:20.200 | Callee said: Biergarten ist belegt, drinnen ginge.",
                "19:04:28.400 | Bot is speaking: Inside is acceptable to us.",
                "19:04:40.100 | Call ended; syncing final Calling result."
            ]
        }
    },

    # Scenario 9: Tiered Concessions Negotiation Cascade (MUSTER.md)
    "tiered_concessions_cascade": {
        "rest_trattoria_luigi": {
            "status": CallStatus.COMPLETED,
            "structured_result": {
                "table_available": True,
                "reservation_confirmed": True,
                "reservation_date_confirmed": "{reservation_date}",
                "reservation_time_confirmed": "{reservation_time}",
                "seating_preference_met": True,
                "booking_fee_eur": 15,
                "authority_steps_applied": ["booking_fee"],
                "callback_number": "+441632960001",
                "rejection_reason": None
            },
            "post_summary": "Table reserved at Trattoria Bella Luigi with the authorised 15 EUR booking fee.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "BOT", "text": "Hello, calling on behalf of {customer_name}. Do you have a regular table for {party_size} people on {reservation_date} at {reservation_time}?"},
                {"ts": "00:00:12", "speaker": "USER", "text": "Regular tables are fully booked, but we have a private dining room table available with a 15 Euro booking deposit."},
                {"ts": "00:00:20", "speaker": "BOT", "text": "Under our Tier 2 guidelines, a 15 Euro deposit is acceptable. Please confirm the reservation for {party_size} guests under {customer_name}."},
                {"ts": "00:00:28", "speaker": "USER", "text": "Confirmed! Private table reserved under {customer_name}."}
            ],
            "activity": [
                "17:37:05.100 | Bot initialized.",
                "17:37:44.200 | Call ringing (~40s setup latency).",
                "17:37:49.500 | Call connected.",
                "17:37:50.700 | Bot is speaking: Hello, calling on behalf of {customer_name}.",
                "17:37:52.200 | Callee said: Regular booked, private room +15 deposit.",
                "17:38:00.100 | Call ended; syncing final Calling result."
            ]
        }
    }
}
