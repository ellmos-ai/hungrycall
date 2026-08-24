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
        '+441632960090' -> '+491 ••• ••••090'
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


# National format: a spoken or typed German number without country code —
# leading 0, then 8-13 more digits, optionally spaced. Field trial 2026-08-11:
# the callee dictated a national-format number (e.g. "07700900090") and it
# sailed unmasked through transcripts and results because only +49-style
# forms were recognised.
NATIONAL_IN_TEXT_REGEX = re.compile(r"(?<![\d+])0[1-9](?:[ -]?\d){7,12}(?!\d)")


def mask_phones_in_text(text: str) -> str:
    """Mask compact or spaced E.164 and national-format numbers in text.

    Deliberate limitation, not an oversight: this does not catch a number
    spelled out as individual digit words ("null eins sieben neun ...").
    Doing that generically for an UNKNOWN number would false-positive on
    prices, dates, party sizes and every other digit-word sequence in a
    transcript. Where the number is already known (the requester's own
    callback), ``redact_specific_phone`` targets it specifically instead
    (see ``_spelled_out_digits_pattern`` below).
    """
    if not text:
        return text

    def replace(match: re.Match) -> str:
        normalized = re.sub(r"[ -]", "", match.group(0))
        return mask_phone(normalized) if validate_e164(normalized) else match.group(0)

    masked = E164_IN_TEXT_REGEX.sub(replace, text)

    def replace_national(match: re.Match) -> str:
        normalized = re.sub(r"[ -]", "", match.group(0))
        if len(normalized) < 9:
            return match.group(0)
        return mask_phone(normalize_e164(normalized))

    return NATIONAL_IN_TEXT_REGEX.sub(replace_national, masked)


# A voice agent reads the requester's callback number aloud on the call, and
# the STT transcript sometimes returns it as individual German digit words
# rather than digits (field trial 2026-08-11: e.g. "plus vier neun, eins
# sieben sechs, ..." for a number like "+4910004069..."). Neither
# PHONE_CANDIDATE_REGEX (needs a contiguous digit run) nor
# NATIONAL_IN_TEXT_REGEX catches that, so the requester's own number survived
# redaction and reached the stored transcript/receipt unmasked. Worse: the
# digit words can be split across two reconstructed transcript lines, each
# carrying its own "[mm:ss] SPEAKER: " header
# (``LiveCallClient._transcript_from_turns``), when CALL-E's STT happened to
# end one turn mid-number. Because ``redact_specific_phone`` already knows
# the exact number to look for, this does not need general number-word
# parsing (which would also match prices, dates and party sizes, see the
# mask_phones_in_text limitation note above) — it only has to recognise
# THIS number's digits, in order, however the transcript grouped,
# punctuated or turn-broke them.
_GERMAN_DIGIT_WORDS = {
    "0": "null", "1": "eins", "2": "zwei", "3": "drei", "4": "vier",
    "5": "fünf", "6": "sechs", "7": "sieben", "8": "acht", "9": "neun",
}

# Whatever sits between two spoken digit words: ordinary punctuation/
# whitespace, or a whole reconstructed-transcript turn header interrupting
# mid-number ("neun,\n[01:15] BOT: eins" - a real 2026-08-11 field-trial
# shape). The turn header's speaker label is matched generically
# ([A-Za-z?]+), not just BOT/USER, since that value passes through
# uppercased from whatever CALL-E returns.
_DIGIT_WORD_GAP = (
    r"(?:[\s,;-]+|\[\d{1,2}:\d{2}\]\s*[A-Za-z?]+:\s*)+"
)


def _spelled_out_digits_pattern(normalized_phone: str) -> re.Pattern | None:
    """Regex matching ``normalized_phone`` spoken as German digit words."""
    digits = normalized_phone.lstrip("+")
    if not digits.isdigit() or not digits:
        return None
    words = ["plus"] + [_GERMAN_DIGIT_WORDS[digit] for digit in digits]
    body = _DIGIT_WORD_GAP.join(words)
    return re.compile(rf"\b{body}\b", re.IGNORECASE)


def redact_specific_phone(value: Any, phone: str) -> Any:
    """Recursively remove one purpose-bound phone number from API output.

    Restaurant callback numbers remain useful result data. The requester's
    number is transient call authority and must not be echoed into JSON,
    history, receipts or logs.
    """
    normalized = normalize_e164(phone or "")
    if not validate_e164(normalized):
        return value

    spelled_out = _spelled_out_digits_pattern(normalized)

    def redact_text(text: str) -> str:
        text = text.replace(normalized, "[REDACTED-REQUESTER-CALLBACK]")

        def replace(match: re.Match) -> str:
            if normalize_e164(match.group(0)) == normalized:
                return "[REDACTED-REQUESTER-CALLBACK]"
            return match.group(0)

        text = PHONE_CANDIDATE_REGEX.sub(replace, text)
        if spelled_out is not None:
            text = spelled_out.sub("[REDACTED-REQUESTER-CALLBACK]", text)
        return text

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
