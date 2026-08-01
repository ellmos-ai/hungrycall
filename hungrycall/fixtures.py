"""Fixtures and mock responses for dry-run execution without network or account."""

from typing import Dict, List, Any
from hungrycall.models import Restaurant, OpeningHours, CallResult, CallStatus, Mode


SAMPLE_RESTAURANTS: List[Restaurant] = [
    Restaurant(
        id="rest_burger_house",
        name="Burger House Dorfstadt",
        phone="+491701111111",
        cuisines=["Burger", "American", "Fast Food"],
        opening_hours=OpeningHours(
            days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            open_time="11:00",
            close_time="23:00"
        ),
        is_favorite=False,
        supports_delivery=True,
        supports_pickup=True,
        supports_reservation=True,
        address="Dorfstraße 5, 12345 Dorfstadt",
        email="info@burgerhouse.de"
    ),
    Restaurant(
        id="rest_trattoria_luigi",
        name="Trattoria Bella Luigi",
        phone="+491702222222",
        cuisines=["Italian", "Pizza", "Pasta"],
        opening_hours=OpeningHours(
            days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            open_time="12:00",
            close_time="22:00"
        ),
        is_favorite=True,  # Favorite Italian restaurant
        supports_delivery=True,
        supports_pickup=True,
        supports_reservation=True,
        address="Marktplatz 1, 12345 Dorfstadt",
        email="luigi@trattoriabella.de"
    ),
    Restaurant(
        id="rest_asian_wok",
        name="Asia Wok Express",
        phone="+491703333333",
        cuisines=["Asian", "Chinese", "Noodles"],
        opening_hours=OpeningHours(
            days=["Wed", "Thu", "Fri", "Sat", "Sun"],
            open_time="16:00",
            close_time="22:00"
        ),
        is_favorite=False,
        supports_delivery=True,
        supports_pickup=True,
        supports_reservation=False,
        address="Bahnhofstraße 12, 12345 Dorfstadt"
    ),
    Restaurant(
        id="rest_closed_diner",
        name="Late Night Snack Shack",
        phone="+491704444444",
        cuisines=["Burger", "Snack"],
        opening_hours=OpeningHours(
            days=["Fri", "Sat"],
            open_time="22:00",
            close_time="04:00"
        ),
        is_favorite=False,
        supports_delivery=True,
        supports_pickup=True,
        supports_reservation=False,
        address="Industriestraße 8, 12345 Dorfstadt"
    )
]


# Mock responses mapped by (restaurant_id, mode) or fixture scenario preset name
SCENARIO_FIXTURES: Dict[str, Dict[str, Any]] = {
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
                "callback_number": "+491701111111",
                "rejection_reason": None
            },
            "post_summary": "Order placed successfully. Total: 28.50 EUR, ETA: 35 minutes.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "Agent", "text": "Hello, I am an automated assistant calling on behalf of Lukas. Do you deliver to Hauptstraße 12?"},
                {"ts": "00:00:10", "speaker": "Restaurant", "text": "Yes, we deliver to Hauptstraße 12."},
                {"ts": "00:00:15", "speaker": "Agent", "text": "Great! What is the exact total price including delivery fee for 2 Cheeseburgers and 2 Fries?"},
                {"ts": "00:00:22", "speaker": "Restaurant", "text": "The total end price at your door is exactly 28 Euros and 50 Cents."},
                {"ts": "00:00:28", "speaker": "Agent", "text": "Perfect, that is within our 35 Euro limit. Please place the order. How long will it take?"},
                {"ts": "00:00:35", "speaker": "Restaurant", "text": "Order is confirmed! Delivery will take about 35 minutes."},
                {"ts": "00:00:40", "speaker": "Agent", "text": "Thank you very much. Goodbye!"}
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
                "callback_number": "+491701111111",
                "rejection_reason": "Unclear price statement: Restaurant said 'about 30 Euro depending on driver'"
            },
            "post_summary": "Declined order due to unconfirmed vague price quote.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "Agent", "text": "Hello, calling on behalf of Lukas. What is the total price for the burger menu?"},
                {"ts": "00:00:12", "speaker": "Restaurant", "text": "Well, it's so roughly around 30 Euros, depends a bit on the delivery driver fee today."},
                {"ts": "00:00:20", "speaker": "Agent", "text": "I am sorry, I need an exact total price to proceed. Since it is unconfirmed, I cannot place the order. Have a nice evening."}
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
                "callback_number": "+491702222222",
                "rejection_reason": None
            },
            "post_summary": "Order placed successfully at Trattoria Bella Luigi. Total 29.00 EUR.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "Agent", "text": "Hello, calling on behalf of Lukas. Can you deliver to Hauptstraße 12?"},
                {"ts": "00:00:10", "speaker": "Restaurant", "text": "Yes, we deliver there. The total price is exactly 29.00 Euros."},
                {"ts": "00:00:18", "speaker": "Agent", "text": "29.00 EUR is within the 35 EUR limit. Please place the order."},
                {"ts": "00:00:25", "speaker": "Restaurant", "text": "Order received! Delivery in 45 minutes."}
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
                "total_price_eur": 42.00,  # Exceeds 35.00 limit!
                "eta_minutes": 30,
                "order_placed": False,
                "callback_number": "+491701111111",
                "rejection_reason": "Total price 42.00 EUR exceeds budget limit of 35.00 EUR"
            },
            "post_summary": "Declined order: total 42.00 EUR exceeds limit of 35.00 EUR.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "Agent", "text": "Hello, calling on behalf of Lukas. What is the total price for delivery?"},
                {"ts": "00:00:12", "speaker": "Restaurant", "text": "With delivery charge and minimum order, the total is exactly 42 Euros."},
                {"ts": "00:00:20", "speaker": "Agent", "text": "That exceeds our maximum budget limit of 35 Euros. I must politely decline. Goodbye!"}
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
                "callback_number": "+491702222222",
                "rejection_reason": None
            },
            "post_summary": "Order placed successfully at Trattoria Bella Luigi. Total 31.50 EUR.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "Agent", "text": "Hello, calling on behalf of Lukas. Can you deliver for 31.50 EUR total?"},
                {"ts": "00:00:12", "speaker": "Restaurant", "text": "Yes, total is 31.50 Euros. Order placed!"}
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
                "callback_number": "+491702222222",
                "rejection_reason": None
            },
            "post_summary": "Table reserved for 4 people on 2026-08-05 at 19:00.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "Agent", "text": "Hello, calling on behalf of Lukas. Do you have a table for 4 people on 2026-08-05 at 19:00?"},
                {"ts": "00:00:12", "speaker": "Restaurant", "text": "Yes, we have a table available at 19:00."},
                {"ts": "00:00:18", "speaker": "Agent", "text": "Please reserve it under the name Lukas. What is your callback number in case we need to cancel?"},
                {"ts": "00:00:25", "speaker": "Restaurant", "text": "Reserved! Our callback number is +49 170 2222222. See you then!"}
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
                "callback_number": "+491701111111",
                "rejection_reason": None
            },
            "post_summary": "Pickup order placed. Total 22.00 EUR, ready in 20 minutes.",
            "transcript": [
                {"ts": "00:00:05", "speaker": "Agent", "text": "Hello, calling on behalf of Lukas. Can we place a pickup order for 2 Burgers?"},
                {"ts": "00:00:10", "speaker": "Restaurant", "text": "Yes, pickup is available. Total price is 22 Euros."},
                {"ts": "00:00:16", "speaker": "Agent", "text": "22 Euros is within our 25 Euro limit. Please place the order. When will it be ready?"},
                {"ts": "00:00:22", "speaker": "Restaurant", "text": "It will be ready in 20 minutes."}
            ]
        }
    }
}
