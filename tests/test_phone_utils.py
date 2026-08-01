"""Unit tests for phone number validation and masking."""

from hungrycall.phone_utils import validate_e164, normalize_e164, mask_phone


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
