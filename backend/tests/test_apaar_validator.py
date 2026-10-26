"""Tests for APAAR ID normalizer and validator."""

import pytest
from app.validation.apaar_validator import (
    generate_verhoeff_check_digit,
    normalize_apaar_id,
    validate_apaar,
    validate_verhoeff,
)


def test_normalize_hindi_devanagari_digits():
    """Verify Devanagari Hindi digits convert accurately to ASCII digits."""
    hindi_apaar = "१२३४५६७८९०१२"
    normalized = normalize_apaar_id(hindi_apaar)
    assert normalized == "123456789012"


def test_normalize_spaces_and_hyphens():
    """Verify spaces, dashes, slashes, and periods are stripped."""
    assert normalize_apaar_id(" 2000-1234-5678 ") == "200012345678"
    assert normalize_apaar_id("2000.1234.5678") == "200012345678"
    assert normalize_apaar_id("2000/1234/5678") == "200012345678"
    assert normalize_apaar_id("2000 1234 5678") == "200012345678"


def test_validate_clean_12_digits():
    """Clean 12-digit number returns is_valid=True and severity=OK."""
    res = validate_apaar("200012345678")
    assert res.is_valid is True
    assert res.severity == "OK"
    assert res.normalized_id == "200012345678"


def test_validate_empty_and_short():
    """Empty or non-12-digit numbers fail with ERROR."""
    res = validate_apaar("")
    assert res.is_valid is False
    assert res.error_code == "APAAR_EMPTY"

    res = validate_apaar("12345")
    assert res.is_valid is False
    assert res.error_code == "APAAR_INVALID_FORMAT"

    res = validate_apaar("123456789012345")
    assert res.is_valid is False
    assert res.error_code == "APAAR_INVALID_FORMAT"


def test_validate_non_numeric():
    """Non-numeric characters in input fail validation."""
    res = validate_apaar("20001234ABCD")
    assert res.is_valid is False
    assert res.error_code == "APAAR_INVALID_FORMAT"


def test_validate_trivial_patterns_warning():
    """All-same-digits or sequential patterns return is_valid=True with WARNING severity."""
    # All identical
    res = validate_apaar("111111111111")
    assert res.is_valid is True
    assert res.severity == "WARNING"
    assert res.error_code == "APAAR_TRIVIAL_PATTERN"
    assert "identical" in res.message.lower()

    # Sequential ascending
    res = validate_apaar("123456789012")
    assert res.is_valid is True
    assert res.severity == "WARNING"
    assert "sequential" in res.message.lower() or "ascending" in res.message.lower()

    # Sequential descending
    res = validate_apaar("987654321098")
    assert res.is_valid is True
    assert res.severity == "WARNING"


def test_verhoeff_checksum_algorithm():
    """Test Verhoeff check digit generation and validation."""
    prefix = "20000000001"
    check_digit = generate_verhoeff_check_digit(prefix)
    full_number = prefix + check_digit

    assert len(full_number) == 12
    assert validate_verhoeff(full_number) is True

    # Mutate a single digit - should fail Verhoeff check
    corrupt_digit = "9" if full_number[-1] != "9" else "0"
    corrupt_number = full_number[:-1] + corrupt_digit
    assert validate_verhoeff(corrupt_number) is False


def test_validate_apaar_with_checksum_flag():
    """Optional enforce_checksum flag validates Verhoeff."""
    prefix = "20000000001"
    valid_id = prefix + generate_verhoeff_check_digit(prefix)
    invalid_id = prefix + ("9" if valid_id[-1] != "9" else "0")

    # When enforce_checksum=False, both pass format check
    assert validate_apaar(valid_id, enforce_checksum=False).is_valid is True
    assert validate_apaar(invalid_id, enforce_checksum=False).is_valid is True

    # When enforce_checksum=True, invalid checksum fails with ERROR
    assert validate_apaar(valid_id, enforce_checksum=True).is_valid is True
    res_invalid = validate_apaar(invalid_id, enforce_checksum=True)
    assert res_invalid.is_valid is False
    assert res_invalid.error_code == "APAAR_CHECKSUM_FAILED"
