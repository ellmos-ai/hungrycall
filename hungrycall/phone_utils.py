"""Phone number validation and masking utilities adhering to E.164 standards."""

import re
from typing import Any

# E.164 pattern: Starts with '+', followed by country code and subscriber number (7 to 15 digits total)
E164_REGEX = re.compile(r"^\+[1-9]\d{6,14}$")
E164_IN_TEXT_REGEX = re.compile(r"\+[1-9](?:[ -]?\d){6,14}")
PHONE_CANDIDATE_REGEX = re.compile(
    r"(?<!\w)(?:\+|00)?[0-9][0-9 ()/.-]{5,24}[0-9](?!\w)"
)


def validate_e164(phone: str) -> bool:
    """Validate if a phone number strictly follows E.164 format."""
    if not phone:
        return False
    # Strip spaces or hyphens for clean checking if passed dirty
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    return bool(E164_REGEX.match(cleaned))


def normalize_e164(phone: str, default_country: str = "+49") -> str:
    """Normalize a phone number string into strict E.164 format."""
    # OSM commonly contains display formatting (spaces, slashes, parentheses)
    # and occasionally an optional German trunk marker such as ``+49 (0)``.
    # A semicolon means multiple numbers; HungryCall calls only the first one.
    first = re.split(r"[;,]", phone, maxsplit=1)[0].strip().replace("(0)", "")
    cleaned = re.sub(r"[^0-9+]", "", first)
    if cleaned.count("+") > 1 or ("+" in cleaned and not cleaned.startswith("+")):
        return cleaned
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    elif cleaned.startswith("0"):
        cleaned = default_country + cleaned[1:]
    elif not cleaned.startswith("+"):
        cleaned = default_country + cleaned
    return cleaned


def mask_phone(phone: str) -> str:
    """Mask phone numbers for safe display in logs, outputs, and reports.
    
    Example:
        '+491701234567' -> '+49 ••• ••••567'
    """
    if not phone:
        return "[MASKED-PHONE]"
    
    cleaned = phone.strip().replace(" ", "")
    if len(cleaned) < 6:
        return "+•••"
    
    prefix = cleaned[:4]  # e.g. "+491" or "+49"
    suffix = cleaned[-3:] # e.g. "567"
    masked_middle = " ••• ••••"
    
    return f"{prefix}{masked_middle}{suffix}"


def mask_phones_in_text(text: str) -> str:
    """Mask compact or spaced E.164 numbers in API text and transcripts."""
    if not text:
        return text

    def replace(match: re.Match) -> str:
        normalized = re.sub(r"[ -]", "", match.group(0))
        return mask_phone(normalized) if validate_e164(normalized) else match.group(0)

    return E164_IN_TEXT_REGEX.sub(replace, text)


def redact_specific_phone(value: Any, phone: str) -> Any:
    """Recursively remove one purpose-bound phone number from API output.

    Restaurant callback numbers remain useful result data. The requester's
    number is transient call authority and must not be echoed into JSON,
    history, receipts or logs.
    """
    normalized = normalize_e164(phone or "")
    if not validate_e164(normalized):
        return value

    def redact_text(text: str) -> str:
        text = text.replace(normalized, "[REDACTED-REQUESTER-CALLBACK]")

        def replace(match: re.Match) -> str:
            if normalize_e164(match.group(0)) == normalized:
                return "[REDACTED-REQUESTER-CALLBACK]"
            return match.group(0)

        return PHONE_CANDIDATE_REGEX.sub(replace, text)

    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key == "requester_callback_number":
                continue
            redacted = redact_specific_phone(item, normalized)
            if key == "callback_number" and redacted == "[REDACTED-REQUESTER-CALLBACK]":
                continue
            cleaned[key] = redacted
        return cleaned
    if isinstance(value, list):
        return [redact_specific_phone(item, normalized) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_specific_phone(item, normalized) for item in value)
    return value
