"""JSON Schemas for CALL-E result_schema definition across all HungryCall modes."""

from copy import deepcopy
from typing import Any, Dict, Optional

from hungrycall.models import Mode, OrderChain
from hungrycall.order_chains import ORDER_CHAIN_RESULT_SCHEMA


DELIVERY_RESULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["delivers_to_address", "price_known"],
    "properties": {
        "delivers_to_address": {
            "type": "boolean",
            "description": "True if restaurant delivers to specified address, False otherwise."
        },
        "price_known": {
            "type": "boolean",
            "description": "True if an EXACT total price in EUR was quoted. False if price is vague ('about 30', 'depends')."
        },
        "total_price_eur": {
            "type": "number",
            "description": "Total final amount at doorstep including food, delivery fee, and minimum order values."
        },
        "eta_minutes": {
            "type": "integer",
            "description": "Estimated delivery time in minutes."
        },
        "order_placed": {
            "type": "boolean",
            "description": "True if order was officially placed, False if rejected or failed."
        },
        "callback_number": {
            "type": "string",
            "description": "Direct callback phone number for caller verification or modifications."
        },
        "rejection_reason": {
            "type": "string",
            "description": "Detailed explanation if delivery, price, or order was declined."
        }
    }
}


RESERVATION_RESULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "table_available",
        "reservation_confirmed",
        "reservation_date_confirmed",
        "reservation_time_confirmed",
        "seating_preference_met",
        "booking_fee_eur",
        "authority_steps_applied",
    ],
    "properties": {
        "table_available": {
            "type": "boolean",
            "description": "True if table is available for requested date, time, and party size."
        },
        "reservation_confirmed": {
            "type": "boolean",
            "description": "True if reservation has been successfully booked under caller's name."
        },
        "reservation_date_confirmed": {
            "type": "string",
            "description": "Confirmed reservation date in YYYY-MM-DD format."
        },
        "reservation_time_confirmed": {
            "type": "string",
            "description": "Confirmed reservation time in 24-hour HH:MM format."
        },
        "seating_confirmed": {
            "type": "string",
            "description": "The seating or table preference the restaurant actually confirmed."
        },
        "seating_preference_met": {
            "type": "boolean",
            "description": "True if the user's specific custom seating preference was confirmed; otherwise False."
        },
        "booking_fee_eur": {
            "type": "number",
            "description": "Exact booking fee or deposit in EUR. Return 0 if there is none."
        },
        "authority_steps_applied": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["earlier_time", "later_time", "booking_fee"]
            },
            "description": "Reservation fallback authority used, in the order it was applied. Empty for the exact fee-free request."
        },
        "callback_number": {
            "type": "string",
            "description": "Direct callback phone number of restaurant for cancellation or changes."
        },
        "rejection_reason": {
            "type": "string",
            "description": "Explanation if table is fully booked or reservation declined."
        }
    }
}


PICKUP_RESULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["pickup_available", "price_known"],
    "properties": {
        "pickup_available": {
            "type": "boolean",
            "description": "True if restaurant accepts pickup order for requested items."
        },
        "price_known": {
            "type": "boolean",
            "description": "True if an EXACT total price in EUR was quoted. False if vague."
        },
        "total_price_eur": {
            "type": "number",
            "description": "Total final price for pickup order in EUR."
        },
        "prep_time_minutes": {
            "type": "integer",
            "description": "Estimated preparation time in minutes until ready for pickup."
        },
        "order_placed": {
            "type": "boolean",
            "description": "True if pickup order was placed, False otherwise."
        },
        "callback_number": {
            "type": "string",
            "description": "Direct callback phone number of restaurant."
        },
        "rejection_reason": {
            "type": "string",
            "description": "Reason if pickup order was declined or not available."
        }
    }
}


def get_result_schema(mode: Mode, order_chain: Optional[OrderChain] = None) -> Dict[str, Any]:
    """Retrieve the designated result_schema for a given HungryCall mode."""
    if mode == Mode.DELIVERY:
        schema = DELIVERY_RESULT_SCHEMA
    elif mode == Mode.RESERVATION:
        schema = RESERVATION_RESULT_SCHEMA
    elif mode == Mode.PICKUP:
        schema = PICKUP_RESULT_SCHEMA
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    if order_chain is None:
        return schema
    result = deepcopy(schema)
    result["required"] = list(result.get("required", [])) + ["order_chain_results"]
    result["properties"]["order_chain_results"] = deepcopy(ORDER_CHAIN_RESULT_SCHEMA)
    return result
