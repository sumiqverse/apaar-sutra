"""Ghost-student detection heuristics.

Identifies fabricated or phantom student records through:
1. Bursts of admissions on identical timestamps or tight time windows (e.g. within 180 seconds).
2. Sequential or arithmetic patterned APAAR IDs within an institutional cohort.
3. Repeating DOB and parent-name demographic clusters within the same institution/program.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
import re


class GhostStudentDetector:
    """Heuristic engine detecting artificial, cloned, and phantom student records."""

    @staticmethod
    def detect_timestamp_bursts(
        enrolments: List[Dict[str, Any]],
        window_seconds: int = 180,
        min_cluster_size: int = 5,
    ) -> List[Dict[str, Any]]:
        """Identify clusters of admissions occurring within a tight sliding window."""
        valid_items = []
        for e in enrolments:
            ts = e.get("created_at") or e.get("admission_date")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    continue
            if isinstance(ts, datetime):
                valid_items.append((ts, str(e.get("id")), str(e.get("student_id"))))

        if len(valid_items) < min_cluster_size:
            return []

        # Sort by timestamp
        valid_items.sort(key=lambda x: x[0])
        clusters: List[Dict[str, Any]] = []
        n = len(valid_items)
        i = 0

        while i < n:
            start_time, en_id, st_id = valid_items[i]
            window_end = start_time + timedelta(seconds=window_seconds)

            j = i + 1
            cluster_enrolment_ids = [en_id]
            cluster_student_ids = [st_id]

            while j < n and valid_items[j][0] <= window_end:
                cluster_enrolment_ids.append(valid_items[j][1])
                cluster_student_ids.append(valid_items[j][2])
                j += 1

            if len(cluster_enrolment_ids) >= min_cluster_size:
                clusters.append({
                    "start_time": start_time.isoformat(),
                    "window_seconds": window_seconds,
                    "student_count": len(cluster_enrolment_ids),
                    "enrolment_ids": cluster_enrolment_ids,
                    "student_ids": cluster_student_ids,
                })
                # Advance beyond this cluster
                i = j
            else:
                i += 1

        return clusters

    @staticmethod
    def detect_sequential_apaars(
        students: List[Dict[str, Any]],
        min_run_length: int = 4,
    ) -> List[Dict[str, Any]]:
        """Detect consecutive or arithmetic progressions in APAAR IDs within an institution."""
        numeric_items = []
        for s in students:
            apaar = str(s.get("apaar_id") or "")
            if apaar.isdigit() and len(apaar) == 12:
                numeric_items.append((int(apaar), apaar, str(s.get("id"))))

        if len(numeric_items) < min_run_length:
            return []

        numeric_items.sort(key=lambda x: x[0])
        runs: List[Dict[str, Any]] = []
        n = len(numeric_items)
        i = 0

        while i < n:
            val, apaar_str, st_id = numeric_items[i]
            current_run = [numeric_items[i]]

            j = i + 1
            while j < n:
                prev_val = current_run[-1][0]
                curr_val = numeric_items[j][0]
                diff = curr_val - prev_val

                # Check if consecutive (+1)
                if diff == 1:
                    current_run.append(numeric_items[j])
                    j += 1
                else:
                    break

            if len(current_run) >= min_run_length:
                runs.append({
                    "start_apaar": current_run[0][1],
                    "end_apaar": current_run[-1][1],
                    "run_length": len(current_run),
                    "student_ids": [item[2] for item in current_run],
                })
                i = j
            else:
                i += 1

        return runs

    @staticmethod
    def detect_repeating_demographic_clusters(
        students: List[Dict[str, Any]],
        min_cluster_size: int = 3,
    ) -> List[Dict[str, Any]]:
        """Identify clusters of students sharing identical DOB and parent name/blind index."""
        groups: Dict[Tuple[str, str], List[str]] = defaultdict(list)

        for s in students:
            dob = str(s.get("dob") or s.get("dob_enc") or s.get("dob_bidx") or "")
            parent = str(s.get("parent_name") or s.get("parent_name_enc") or s.get("parent_bidx") or "")
            st_id = str(s.get("id"))

            if dob and parent:
                # Normalize parent token
                clean_parent = re.sub(r"[^\w]", "", parent.lower())
                groups[(dob, clean_parent)].append(st_id)

        clusters: List[Dict[str, Any]] = []
        for (dob, parent_key), member_ids in groups.items():
            if len(member_ids) >= min_cluster_size:
                clusters.append({
                    "dob": dob,
                    "parent_key": parent_key,
                    "student_count": len(member_ids),
                    "student_ids": member_ids,
                })

        clusters.sort(key=lambda x: x["student_count"], reverse=True)
        return clusters

    @classmethod
    def analyze_institution(
        cls,
        institution_id: str,
        enrolments: List[Dict[str, Any]],
        students: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Produce comprehensive ghost-student heuristic assessment for an institution."""
        bursts = cls.detect_timestamp_bursts(enrolments)
        sequential = cls.detect_sequential_apaars(students)
        repeating = cls.detect_repeating_demographic_clusters(students)

        # Flagged student ID set
        suspect_ids: Set[str] = set()
        for b in bursts:
            suspect_ids.update(b["student_ids"])
        for s in sequential:
            suspect_ids.update(s["student_ids"])
        for r in repeating:
            suspect_ids.update(r["student_ids"])

        total_students = max(len(students), len(enrolments), 1)
        suspect_ratio = len(suspect_ids) / total_students

        # Compute heuristic risk score: 0 to 100
        score = 0.0
        if bursts:
            score += min(35.0, len(bursts) * 15.0)
        if sequential:
            score += min(35.0, len(sequential) * 15.0)
        if repeating:
            score += min(30.0, len(repeating) * 10.0)

        # Ratio multiplier
        score = min(100.0, score + (suspect_ratio * 50.0))

        return {
            "institution_id": str(institution_id),
            "heuristic_risk_score": round(score, 1),
            "suspect_students_count": len(suspect_ids),
            "suspect_students_ratio": round(suspect_ratio, 4),
            "burst_admission_clusters": bursts,
            "sequential_apaar_runs": sequential,
            "repeating_demographic_clusters": repeating,
            "has_ghost_indicators": len(suspect_ids) > 0,
        }
