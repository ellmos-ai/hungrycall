"""Unit tests for phone number validation and masking."""

from hungrycall.phone_utils import validate_e164, normalize_e164, mask_phone


def test_validate_e164_valid():
    assert validate_e164("+491701234567") is True
    assert validate_e164("+15551234567") is True
    assert validate_e164("+442079460999") is True


def test_validate_e164_invalid():
    assert validate_e164("01701234567") is False
    assert validate_e164("12345") is False
    assert validate_e164("") is False
    assert validate_e164("invalid_phone") is False


def test_normalize_e164():
    assert normalize_e164("01701234567") == "+491701234567"
    assert normalize_e164("00491701234567") == "+491701234567"
    assert normalize_e164("+49 170 1234567") == "+491701234567"


def test_mask_phone():
    masked = mask_phone("+491701234567")
    assert "170" in masked or "+49" in masked
    assert "1234" not in masked  # Middle numbers masked
    assert "567" in masked       # Suffix kept for callback reference
    assert "•••" in masked
