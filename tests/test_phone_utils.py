"""Unit tests for phone number validation and masking."""

from hungrycall.phone_utils import (
    mask_phone,
    mask_phones_in_text,
    normalize_e164,
    redact_specific_phone,
    validate_e164,
)

# Fictional throughout this file (AGENTS.md: examples only with fictional
# numbers) - never the operator's real callback number.
FICTIONAL_CALLBACK = "+4910004069000"


def test_validate_e164_valid():
    assert validate_e164("+441632960090") is True
    assert validate_e164("+12025550123") is True
    assert validate_e164("+442079460999") is True


def test_validate_e164_invalid():
    assert validate_e164("07700900090") is False
    assert validate_e164("12345") is False
    assert validate_e164("") is False
    assert validate_e164("invalid_phone") is False


def test_normalize_e164():
    assert normalize_e164("07700900090") == "+441632960090"
    assert normalize_e164("00441632960090") == "+441632960090"
    assert normalize_e164("+44 1632 960090") == "+441632960090"


def test_mask_phone():
    masked = mask_phone("+441632960090")
    assert "+49" in masked
    assert "3920" not in masked  # Middle numbers masked
    assert "090" in masked       # Suffix kept for callback reference
    assert "•••" in masked


def test_mask_phone_inside_api_text():
    text = "Callback +441632960090; second +44 20 79460090."
    masked = mask_phones_in_text(text)
    assert "+441632960090" not in masked
    assert "+44 20 79460090" not in masked
    assert masked.endswith("••• ••••090; second +493 ••• ••••090.")


def test_national_format_numbers_are_masked_in_text():
    """Field trial 2026-08-11: a dictated national-format number (fictional
    example here, e.g. '07700900090') sailed unmasked through transcripts
    because only +49-style forms were recognised."""
    from hungrycall.phone_utils import mask_phones_in_text

    masked = mask_phones_in_text("dann nehme ich die 07700900090 als Rückrufnummer")
    assert "07700900090" not in masked
    assert "•••" in masked
    spaced = mask_phones_in_text("unter 07700 900 09 0 erreichbar")
    assert "123" not in spaced.replace("•", "")
    # Harmless digits stay: prices, years, times, house numbers, order ids.
    for harmless in ("17 Euro", "um 20:45 Uhr", "im Jahr 2026",
                     "Hausnummer 12", "Bestellnummer 4711"):
        assert mask_phones_in_text(harmless) == harmless


def test_spelled_out_digit_words_of_a_known_number_are_redacted():
    """Field trial 2026-08-11: the voice agent read the requester's own
    callback number aloud as individual German digit words, which neither
    PHONE_CANDIDATE_REGEX (redact_specific_phone) nor mask_phones_in_text
    (no contiguous digit run) recognised as the same number."""
    text = "Die Rückrufnummer ist plus vier neun, eins null null, null vier null, sechs neun null, null null."
    redacted = redact_specific_phone(text, FICTIONAL_CALLBACK)
    assert "vier" not in redacted
    assert "neun" not in redacted
    assert "[REDACTED-REQUESTER-CALLBACK]" in redacted


def test_spelled_out_digit_words_split_across_a_transcript_turn_header():
    """The exact 2026-08-11 shape: CALL-E's STT ended one turn mid-number, so
    LiveCallClient._transcript_from_turns() reconstructed it as two lines,
    each carrying its own "[mm:ss] SPEAKER: " header in between the digit
    words."""
    text = (
        "[01:10] BOT: Die direkte Rückrufnummer ist plus vier neun,\n"
        "[01:15] BOT: eins null null, null vier null, sechs neun null, null null."
    )
    redacted = redact_specific_phone(text, FICTIONAL_CALLBACK)
    assert "[REDACTED-REQUESTER-CALLBACK]" in redacted
    assert "vier" not in redacted
    assert "sieben" not in redacted
    # The rest of the sentence, and the turn headers themselves, survive.
    assert "[01:10] BOT:" in redacted
    assert "Die direkte Rückrufnummer ist" in redacted


def test_spelled_out_digits_of_a_different_number_are_left_alone():
    """Only the KNOWN target number is redacted -- an unrelated spoken digit
    sequence (e.g. a price or another party's number) is not touched, unlike
    a general number-word parser would risk."""
    text = "Das macht acht Euro fünfzig, und die Uhrzeit ist neun Uhr."
    assert redact_specific_phone(text, FICTIONAL_CALLBACK) == text


def test_digit_form_redaction_is_unaffected_by_the_spelled_out_fix():
    """No regression: the pre-existing compact-digit redaction path still
    works exactly as before."""
    text = f"Rückruf unter {FICTIONAL_CALLBACK} jederzeit möglich."
    redacted = redact_specific_phone(text, FICTIONAL_CALLBACK)
    assert FICTIONAL_CALLBACK not in redacted
    assert "[REDACTED-REQUESTER-CALLBACK]" in redacted
