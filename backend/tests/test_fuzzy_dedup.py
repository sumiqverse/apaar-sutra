"""Unit tests for Indian-name aware fuzzy deduplication (backend/app/ml/fuzzy_dedup.py)."""

from datetime import date
import pytest
from app.ml.fuzzy_dedup import IndianNameNormalizer, CandidateBlocker, FuzzyDeduplicator


def test_indian_name_normalizer_honorifics():
    assert IndianNameNormalizer.normalize("Shri Rajesh Kumar") == "rajesh kumar"
    assert IndianNameNormalizer.normalize("Dr. Priya Sharma") == "priya sharma"
    assert IndianNameNormalizer.normalize("Smt. Laxmi Devi") == "lakshmi devi"
    assert IndianNameNormalizer.normalize("Kumari Diksha Patel") == "deeksha patel"


def test_indian_name_normalizer_transliterations():
    # Mohammad variants
    assert IndianNameNormalizer.normalize("Mohammad Ali") == "mohammed ali"
    assert IndianNameNormalizer.normalize("Mohd. Ali") == "mohammed ali"
    assert IndianNameNormalizer.normalize("Md Ali") == "mohammed ali"

    # Chaudhary variants
    assert IndianNameNormalizer.normalize("Suresh Choudhary") == "suresh chaudhary"
    assert IndianNameNormalizer.normalize("Suresh Chowdhury") == "suresh chaudhary"

    # Patel / Patil
    assert IndianNameNormalizer.normalize("Amit Patil") == "amit patel"


def test_phonetic_blocking_key_generation():
    # Vipin vs Bipin (V/W and B equivalence in phonetic key)
    key_vipin = IndianNameNormalizer.generate_phonetic_key("Vipin")
    key_bipin = IndianNameNormalizer.generate_phonetic_key("Bipin")
    # Both start with labial consonants mapped in same phonetic group
    assert key_vipin[1:] == key_bipin[1:]

    # Aspiration invariance (e.g. Bharat vs Barat)
    key_bharat = IndianNameNormalizer.generate_phonetic_key("Bharat")
    key_barat = IndianNameNormalizer.generate_phonetic_key("Barat")
    assert key_bharat == key_barat


def test_fuzzy_deduplicator_initials_matching():
    dedup = FuzzyDeduplicator(similarity_threshold=85.0)
    score = dedup.compare_names("S. K. Sharma", "Suresh Kumar Sharma")
    assert score >= 90.0


def test_fuzzy_deduplicator_transliteration_match():
    dedup = FuzzyDeduplicator(similarity_threshold=85.0)
    score = dedup.compare_names("Mohammad Irfan Choudhary", "Mohd Irfan Chowdhury")
    assert score >= 95.0


def test_fuzzy_deduplicator_find_duplicates_blocked():
    records = [
        {"id": "st-1", "name": "Aarav Sharma", "dob": date(2005, 5, 10), "apaar_id": "100000000001"},
        {"id": "st-2", "name": "Arav Sharma", "dob": date(2005, 5, 10), "apaar_id": None},  # Duplicate!
        {"id": "st-3", "name": "Vikram Singh", "dob": date(2005, 8, 20), "apaar_id": "100000000003"},
        {"id": "st-4", "name": "Sneha Gupta", "dob": date(2004, 3, 15), "apaar_id": "100000000004"},
    ]

    dedup = FuzzyDeduplicator(similarity_threshold=85.0)
    duplicates = dedup.find_duplicates(records)

    assert len(duplicates) == 1
    dup = duplicates[0]
    assert {dup["student_a_id"], dup["student_b_id"]} == {"st-1", "st-2"}
    assert dup["similarity_score"] >= 85.0
    assert dup["dob_year"] == "2005"
