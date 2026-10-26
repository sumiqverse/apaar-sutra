"""Validation rule engine for 12-digit APAAR ID syntax and checksum."""

from typing import Tuple


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

# Verhoeff algorithm permutation table
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

# Inverse table
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def validate_verhoeff_checksum(number_str: str) -> bool:
    """Validate Verhoeff checksum for numeric string."""
    c = 0
    reversed_digits = [int(ch) for ch in reversed(number_str)]
    for i, digit in enumerate(reversed_digits):
        c = _D[c][_P[i % 8][digit]]
    return c == 0


def generate_verhoeff_check_digit(number_str: str) -> str:
    """Generate the Verhoeff check digit for a string of digits."""
    c = 0
    reversed_digits = [int(ch) for ch in reversed(number_str)]
    for i, digit in enumerate(reversed_digits):
        c = _D[c][_P[(i + 1) % 8][digit]]
    return str(_INV[c])


def validate_apaar_id(apaar_id: str) -> Tuple[bool, str]:
    """Validate an APAAR ID for length, digit conformity, non-triviality, and checksum."""
    if not isinstance(apaar_id, str):
        return False, "APAAR ID must be a string."

    clean = "".join(ch for ch in apaar_id if ch.isdigit())
    if len(clean) != 12:
        return False, f"APAAR ID must be exactly 12 numeric digits (got {len(clean)})."

    if clean.startswith("0") or clean.startswith("1"):
        return False, "APAAR ID must not start with 0 or 1."

    # Reject repetitive trivial sequences (e.g., 999999999999, 123412341234)
    if len(set(clean)) <= 2:
        return False, "APAAR ID appears to be a trivial sequence."

    if not validate_verhoeff_checksum(clean):
        return False, "APAAR ID failed Verhoeff mathematical checksum verification."

    return True, "Valid APAAR ID"
