"""Safety and compliance controls for HungryCall."""

import hashlib
import time

from hungrycall.phone_utils import validate_e164

PROHIBITED_KEYWORDS: list[str] = [
    "hospital", "doctor", "police", "fire", "emergency", "ambulance",
    "court", "lawyer", "legal", "bank", "credit card", "tax", "medical",
    "notarzt", "krankenhaus", "polizei", "feuerwehr", "gericht", "anwalt"
]

SINGAPORE_ENDPOINT_NOTICE = (
    "NOTICE: CALL-E voice agent operates via AiRudder servers located in Singapore "
    "(https://seleven-mcp-sg.airudder.com). Only minimal data required for food "
    "ordering/reservation is transmitted."
)


class SafetyError(Exception):
    """Raised when a safety rule or compliance check is violated."""


def verify_content_safety(food_prompt: str, notes: str = "") -> None:
    """Check user prompt for prohibited domain content (medical, legal, financial, emergency)."""
    text_to_check = f"{food_prompt} {notes}".lower()
    for kw in PROHIBITED_KEYWORDS:
        if kw in text_to_check:
            raise SafetyError(
                f"Content safety policy violation: Prompt contains prohibited term '{kw}'. "
                "HungryCall is strictly restricted to food orders and restaurant reservations."
            )


def verify_phone_safety(phone: str) -> None:
    """Verify phone number is valid E.164 prior to initiating any call."""
    if not validate_e164(phone):
        raise SafetyError(
            f"Invalid phone number format '{phone}'. Must be a valid E.164 phone number (e.g. +447700900090)."
        )


def verify_live_safety(live_flag: bool, user_confirmed: bool) -> None:
    """Enforce dry-run standard behavior unless live execution is explicitly enabled and confirmed."""
    if live_flag and not user_confirmed:
        raise SafetyError(
            "Live calling requires explicit user confirmation (--confirm-live flag or interactive approval)."
        )


def generate_idempotency_key(mode: str, restaurant_id: str, timestamp_sec: float | None = None) -> str:
    """Generate a unique idempotency key to prevent duplicate calls to the same restaurant."""
    ts = int(timestamp_sec or time.time())
    raw = f"hungrycall:{mode}:{restaurant_id}:{ts // 300}"  # 5-minute bucket idempotency
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"hungrycall-{mode}-{restaurant_id}-{digest}"
