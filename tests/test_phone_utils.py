"""Unit tests for phone number validation and masking."""

from hungrycall.phone_utils import (
    mask_phone,
    mask_phones_in_text,
    normalize_e164,
    validate_e164,
)


def test_validate_e164_valid():
    assert validate_e164("+441632960090") is True
    assert validate_e164("+15551234567") is True
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
    assert "170" in masked or "+49" in masked
    assert "1234" not in masked  # Middle numbers masked
    assert "567" in masked       # Suffix kept for callback reference
    assert "•••" in masked


def test_mask_phone_inside_api_text():
    text = "Callback +441632960090; second +44 20 79460090."
    masked = mask_phones_in_text(text)
    assert "+441632960090" not in masked
    assert "+44 20 79460090" not in masked
    assert masked.endswith("••• ••••567; second +493 ••• ••••567.")


def test_national_format_numbers_are_masked_in_text():
    """Field trial 2026-08-11: a dictated '07700900090' sailed unmasked through
    transcripts because only +49-style forms were recognised."""
    from hungrycall.phone_utils import mask_phones_in_text

    masked = mask_phones_in_text("dann nehme ich die 07700900090 als Rückrufnummer")
    assert "07700900090" not in masked
    assert "•••" in masked
    spaced = mask_phones_in_text("unter 07700 900 09 0 erreichbar")
    assert "531" not in spaced.replace("•", "")
    # Harmless digits stay: prices, years, times, house numbers, order ids.
    for harmless in ("17 Euro", "um 20:45 Uhr", "im Jahr 2026",
                     "Hausnummer 12", "Bestellnummer 4711"):
        assert mask_phones_in_text(harmless) == harmless
