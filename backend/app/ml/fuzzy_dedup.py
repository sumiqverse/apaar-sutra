"""Record-level fuzzy deduplication engine with Indian-name awareness and phonetic blocking.

Scalable design:
1. IndianNameNormalizer: Standardizes initials, removes honorifics, and maps common
   spelling/transliteration variants (e.g., Mohammad/Mohammed/Mohd, Laxmi/Lakshmi).
2. PhoneticBlocker: Generates phonetic keys adapted for Indian phonology (V/W, S/SH, B/V,
   aspirated consonants KH/GH/DH/BH/TH).
3. Candidate Blocking: Partitions candidates by (dob_year, phonetic_key) to eliminate
   O(N^2) pairwise comparisons.
4. RapidFuzz Scorer: Computes token-sort and token-set similarity within candidate blocks.
"""

from collections import defaultdict
from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from rapidfuzz import fuzz


# Indian spelling and transliteration synonym mappings
TRANSLITERATION_MAP = {
    # Mohammad variants
    "mohammad": "mohammed",
    "mohd": "mohammed",
    "muhammad": "mohammed",
    "muhammed": "mohammed",
    "md": "mohammed",
    # Chaudhary variants
    "choudhary": "chaudhary",
    "choudhury": "chaudhary",
    "chaudhari": "chaudhary",
    "chowdhury": "chaudhary",
    "chaudhri": "chaudhary",
    # Lakshmi variants
    "laxmi": "lakshmi",
    "laxmee": "lakshmi",
    "lakshmee": "lakshmi",
    # Deeksha variants
    "diksha": "deeksha",
    # Kumar / Singh
    "kmr": "kumar",
    "sngh": "singh",
    # Patel / Patil
    "patil": "patel",
    # B/V alternates
    "vipin": "bipin",
    "varun": "barun",
    "bikas": "vikas",
    "bikash": "vikas",
    # Priya
    "preeya": "priya",
    # Shrestha / Shresth
    "shreshtha": "shrestha",
}

HONORIFICS = {"mr", "ms", "mrs", "shri", "smt", "dr", "kumari", "km", "er"}


class IndianNameNormalizer:
    """Normalizes Indian names for phonetic blocking and fuzzy string matching."""

    @classmethod
    def normalize(cls, name: str) -> str:
        """Strip honorifics, expand/unify transliteration variants, and standardize tokens."""
        if not name:
            return ""
        # Lowercase and remove punctuation except spaces
        clean = re.sub(r"[^\w\s]", " ", name.lower()).strip()
        tokens = clean.split()

        # Remove honorifics
        filtered = [t for t in tokens if t not in HONORIFICS and len(t) > 0]
        if not filtered:
            filtered = tokens

        # Apply transliteration dictionary
        normalized_tokens = [TRANSLITERATION_MAP.get(t, t) for t in filtered]
        return " ".join(normalized_tokens)

    @classmethod
    def generate_phonetic_key(cls, name: str) -> str:
        """Generate phonetic blocking code tailored to Indian names and consonant equivalence."""
        norm = cls.normalize(name)
        if not norm:
            return "Z000"

        # Use first meaningful token (first name or primary initial)
        token = norm.split()[0]
        if not token:
            return "Z000"

        # Indian phonetic rules:
        # 1. Map interchangeable Indian consonants
        s = token
        s = s.replace("ee", "i").replace("oo", "u").replace("aa", "a")
        s = s.replace("kh", "k").replace("gh", "g").replace("ch", "c")
        s = s.replace("jh", "j").replace("th", "t").replace("dh", "d")
        s = s.replace("ph", "p").replace("bh", "b").replace("sh", "s")
        s = s.replace("w", "v")

        # 2. Soundex-style consonant mapping
        first_char = s[0].upper()
        mapping = {
            "B": "1", "F": "1", "P": "1", "V": "1",
            "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
            "D": "3", "T": "3",
            "L": "4",
            "M": "5", "N": "5",
            "R": "6",
        }
        coded = [first_char]
        prev_code = mapping.get(first_char, "")

        for char in s[1:]:
            char_upper = char.upper()
            code = mapping.get(char_upper, "")
            if code and code != prev_code:
                coded.append(code)
                prev_code = code
            elif not code:
                prev_code = ""

        # Pad or truncate to 4 chars
        result = "".join(coded)[:4]
        return result.ljust(4, "0")


class CandidateBlocker:
    """Blocks candidate student records into disjoint buckets to scale deduplication."""

    @staticmethod
    def extract_dob_year(record: Dict[str, Any]) -> str:
        """Extract 4-digit DOB year or fallback to 'UNKNOWN'."""
        dob = record.get("dob") or record.get("dob_enc")
        if isinstance(dob, (date, datetime)):
            return str(dob.year)
        elif isinstance(dob, str) and len(dob) >= 4:
            return dob[:4]
        return "UNKNOWN"

    @classmethod
    def block_records(cls, records: List[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
        """Group records by (dob_year, phonetic_key)."""
        blocks: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        for rec in records:
            name = str(rec.get("name") or rec.get("name_enc") or "")
            phonetic = IndianNameNormalizer.generate_phonetic_key(name)
            dob_yr = cls.extract_dob_year(rec)
            blocks[(dob_yr, phonetic)].append(rec)
        return blocks


class FuzzyDeduplicator:
    """Scalable blocked fuzzy deduplication with Indian name normalization."""

    def __init__(self, similarity_threshold: float = 85.0):
        self.threshold = similarity_threshold

    def compare_names(self, name_a: str, name_b: str) -> float:
        """Calculate weighted RapidFuzz similarity between two normalized Indian names."""
        norm_a = IndianNameNormalizer.normalize(name_a)
        norm_b = IndianNameNormalizer.normalize(name_b)

        if not norm_a or not norm_b:
            return 0.0

        if norm_a == norm_b:
            return 100.0

        # Check for initials match: e.g. "s k sharma" vs "suresh kumar sharma"
        parts_a = norm_a.split()
        parts_b = norm_b.split()
        if len(parts_a) >= 2 and len(parts_b) >= 2:
            # If last names match exactly and initials match
            if parts_a[-1] == parts_b[-1]:
                initials_a = "".join(p[0] for p in parts_a[:-1])
                initials_b = "".join(p[0] for p in parts_b[:-1])
                if initials_a == initials_b:
                    return 95.0

        # RapidFuzz token metrics
        sort_ratio = fuzz.token_sort_ratio(norm_a, norm_b)
        set_ratio = fuzz.token_set_ratio(norm_a, norm_b)
        score = (0.55 * sort_ratio) + (0.45 * set_ratio)
        return round(float(score), 2)

    def find_duplicates(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run blocked fuzzy deduplication across the candidate records."""
        blocks = CandidateBlocker.block_records(records)
        duplicates: List[Dict[str, Any]] = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for (dob_yr, phonetic_key), block_members in blocks.items():
            # If block has only 1 record, no pairs to compare
            if len(block_members) < 2:
                continue

            n = len(block_members)
            for i in range(n):
                for j in range(i + 1, n):
                    rec_a = block_members[i]
                    rec_b = block_members[j]
                    id_a = str(rec_a.get("id"))
                    id_b = str(rec_b.get("id"))

                    if id_a == id_b:
                        continue

                    pair_key = (min(id_a, id_b), max(id_a, id_b))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    name_a = str(rec_a.get("name") or rec_a.get("name_enc") or "")
                    name_b = str(rec_b.get("name") or rec_b.get("name_enc") or "")

                    similarity = self.compare_names(name_a, name_b)

                    if similarity >= self.threshold:
                        duplicates.append({
                            "student_a_id": id_a,
                            "student_b_id": id_b,
                            "student_a_name": name_a,
                            "student_b_name": name_b,
                            "dob_year": dob_yr,
                            "phonetic_block": phonetic_key,
                            "similarity_score": similarity,
                            "apaar_a": rec_a.get("apaar_id"),
                            "apaar_b": rec_b.get("apaar_id"),
                            "institution_a": rec_a.get("institution_id"),
                            "institution_b": rec_b.get("institution_id"),
                        })

        duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
        return duplicates
