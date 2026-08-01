"""Phone number validation and masking utilities adhering to E.164 standards."""

import re

# E.164 pattern: Starts with '+', followed by country code and subscriber number (7 to 15 digits total)
E164_REGEX = re.compile(r"^\+[1-9]\d{6,14}$")


def validate_e164(phone: str) -> bool:
    """Validate if a phone number strictly follows E.164 format."""
    if not phone:
        return False
    # Strip spaces or hyphens for clean checking if passed dirty
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    return bool(E164_REGEX.match(cleaned))


def normalize_e164(phone: str, default_country: str = "+49") -> str:
    """Normalize a phone number string into strict E.164 format."""
    cleaned = phone.strip().replace(" ", "").replace("-", "")
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
