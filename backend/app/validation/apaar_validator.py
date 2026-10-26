"""Centralized, configurable APAAR ID normalizer and validator.

Implements Devanagari digit translation, whitespace/hyphen normalization,
12-digit format check, trivial pattern detection (WARNING), and Verhoeff checksum.
"""

from dataclasses import dataclass
import re
from typing import Optional, Tuple

# Devanagari Hindi Numerals mapping: ०-९ -> 0-9
HINDI_DIGITS_MAP = str.maketrans("०१२३४५६७८९", "0123456789")

# Verhoeff algorithm multiplication table
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# Verhoeff permutation table
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


@dataclass
class ApaarValidationResult:
    is_valid: bool
    normalized_id: str
    severity: str  # "OK", "WARNING", "ERROR"
    error_code: Optional[str] = None
    message: str = "Valid APAAR ID"

    @property
    def warning(self) -> Optional[str]:
        return self.message if self.severity == "WARNING" else None


def normalize_apaar_id(raw_input: Optional[str]) -> str:
    """Normalize raw APAAR ID: convert Hindi digits, remove spaces, dashes, dots."""
    if not raw_input:
        return ""
    # Translate Hindi Devanagari numerals
    translated = str(raw_input).translate(HINDI_DIGITS_MAP)
    # Strip spaces, hyphens, slashes, periods
    clean = re.sub(r"[\s\-\/\.]", "", translated)
    return clean


def validate_verhoeff(numeric_str: str) -> bool:
    """Validate Verhoeff checksum algorithm on 12-digit numeric string."""
    if not numeric_str.isdigit():
        return False
    c = 0
    reversed_digits = [int(ch) for ch in reversed(numeric_str)]
    for i, digit in enumerate(reversed_digits):
        c = _D[c][_P[i % 8][digit]]
    return c == 0


validate_verhoeff_checksum = validate_verhoeff


def generate_verhoeff_check_digit(number_str: str) -> str:
    """Generate the Verhoeff check digit for an 11-digit string."""
    c = 0
    reversed_digits = [int(ch) for ch in reversed(number_str)]
    for i, digit in enumerate(reversed_digits):
        c = _D[c][_P[(i + 1) % 8][digit]]
    return str(_INV[c])


def is_trivial_pattern(digits: str) -> Tuple[bool, str]:
    """Detect trivial patterns like all-identical digits or obvious sequential sequences."""
    # 1. All same digits (e.g. 111111111111, 000000000000)
    if len(set(digits)) == 1:
        return True, "APAAR ID consists of all identical digits (trivial pattern)"

    # 2. Known obvious sequences
    obvious_sequences = {
        "123456789012", "012345678901", "234567890123",
        "987654321098", "876543210987", "098765432109",
    }
    if digits in obvious_sequences:
        return True, "APAAR ID matches an obvious sequential number pattern"

    # 3. Continuous ascending or descending modulo 10
    is_asc = all((int(digits[i]) - int(digits[i - 1])) % 10 == 1 for i in range(1, len(digits)))
    if is_asc:
        return True, "APAAR ID is a continuous ascending sequence"

    is_desc = all((int(digits[i - 1]) - int(digits[i])) % 10 == 1 for i in range(1, len(digits)))
    if is_desc:
        return True, "APAAR ID is a continuous descending sequence"

    return False, ""


def validate_apaar(
    raw_id: Optional[str],
    enforce_checksum: bool = False,
) -> ApaarValidationResult:
    """Validate and normalize APAAR ID.
    
    Returns ApaarValidationResult with status:
    - severity="ERROR" (is_valid=False): Not 12 digits, non-numeric, or blank
    - severity="WARNING" (is_valid=True): Trivial patterns or test sequences
    - severity="OK" (is_valid=True): Clean format
    """
    normalized = normalize_apaar_id(raw_id)

    if not normalized:
        return ApaarValidationResult(
            is_valid=False,
            normalized_id="",
            severity="ERROR",
            error_code="APAAR_EMPTY",
            message="APAAR ID is required and cannot be empty.",
        )

    if len(normalized) != 12 or not normalized.isdigit():
        return ApaarValidationResult(
            is_valid=False,
            normalized_id=normalized,
            severity="ERROR",
            error_code="APAAR_INVALID_FORMAT",
            message=f"APAAR ID must be exactly 12 numeric digits (got '{normalized}').",
        )

    # Check for trivial or sequential test patterns -> WARNING
    is_trivial, trivial_msg = is_trivial_pattern(normalized)
    if is_trivial:
        return ApaarValidationResult(
            is_valid=True,
            normalized_id=normalized,
            severity="WARNING",
            error_code="APAAR_TRIVIAL_PATTERN",
            message=trivial_msg,
        )

    # Optional checksum hook (Verhoeff)
    if enforce_checksum and not validate_verhoeff(normalized):
        return ApaarValidationResult(
            is_valid=False,
            normalized_id=normalized,
            severity="ERROR",
            error_code="APAAR_CHECKSUM_FAILED",
            message="APAAR ID failed Verhoeff checksum validation.",
        )

    return ApaarValidationResult(
        is_valid=True,
        normalized_id=normalized,
        severity="OK",
        message="Valid 12-digit APAAR ID.",
    )
