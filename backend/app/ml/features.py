"""Institution-level feature extraction for ML anomaly detection and risk scoring.

Features extracted per institution per academic year:
1. enrolment_to_intake_ratio: Total active regular enrolment / Approved total intake
2. yoy_enrolment_growth: Year-over-Year enrolment growth rate: (Curr - Prev) / max(Prev, 1)
3. supernumerary_quota_share: Share of NRI, Foreign National, and Supernumerary enrolments
4. warning_record_share: Share of enrolments associated with validation issues or non-clean status
5. apaar_failure_share: Share of enrolments with missing, unverified, or mismatched APAAR IDs
6. admission_burst_index: Max concentration of admissions on a single date or tight window
7. exact_intake_match_freq: Fraction of programs with exact 100% capacity matching (hallmark of synthetic data)
8. surname_entropy: Shannon entropy of student surnames (low entropy signals synthetic/cloned profiles)
9. dob_repeat_ratio: Proportion of duplicate dates of birth (clustering signals synthetic generation)
"""

from collections import Counter
from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.institution import Institution
from app.models.program import Program
from app.models.enrolment import Enrolment
from app.models.student import Student
from app.models.validation import ValidationIssue


FEATURE_NAMES = [
    "enrolment_to_intake_ratio",
    "yoy_enrolment_growth",
    "supernumerary_quota_share",
    "warning_record_share",
    "apaar_failure_share",
    "admission_burst_index",
    "exact_intake_match_freq",
    "surname_entropy",
    "dob_repeat_ratio",
]


def compute_shannon_entropy(items: List[str]) -> float:
    """Compute Shannon entropy in bits for a sequence of tokens."""
    if not items:
        return 0.0
    total = len(items)
    counts = Counter(items)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


class InstitutionFeatureExtractor:
    """Extracts 9-dimensional statistical feature vectors for institutions."""

    @staticmethod
    def extract_from_records(
        institution: Dict[str, Any],
        programs: List[Dict[str, Any]],
        curr_enrolments: List[Dict[str, Any]],
        prev_enrolments: Optional[List[Dict[str, Any]]] = None,
        students: Optional[List[Dict[str, Any]]] = None,
        validation_issues: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, float]:
        """In-memory feature extraction from dictionary records (used in tests and offline pipelines)."""
        prev_enrolments = prev_enrolments or []
        students = students or []
        validation_issues = validation_issues or []

        student_map = {str(s.get("id")): s for s in students}
        total_curr_enrolments = len(curr_enrolments)
        total_prev_enrolments = len(prev_enrolments)

        # 1. Total approved intake across programs in this year
        approved_intake = sum(p.get("approved_intake", 0) for p in programs)
        if approved_intake <= 0:
            approved_intake = institution.get("approved_total_intake", 0)

        # 1. Enrolment to intake ratio (regular quota active enrolments)
        regular_curr = [
            e for e in curr_enrolments
            if e.get("quota_type", "REGULAR") == "REGULAR"
            and not e.get("is_nri", False)
            and not e.get("is_foreign_national", False)
            and e.get("status", "ACTIVE") == "ACTIVE"
        ]
        enrolment_to_intake_ratio = round(len(regular_curr) / max(approved_intake, 1), 4)

        # 2. YoY enrolment growth
        if total_prev_enrolments > 0:
            yoy_growth = (total_curr_enrolments - total_prev_enrolments) / total_prev_enrolments
        else:
            yoy_growth = 0.0
        yoy_enrolment_growth = round(yoy_growth, 4)

        # 3. Supernumerary quota share
        supernumerary_count = sum(
            1 for e in curr_enrolments
            if e.get("quota_type") in ["SUPERNUMERARY", "NRI", "FN", "OCI"]
            or e.get("is_nri")
            or e.get("is_foreign_national")
        )
        supernumerary_quota_share = round(
            supernumerary_count / max(total_curr_enrolments, 1), 4
        )

        # 4. Warning record share
        flagged_enrolment_ids = set()
        for issue in validation_issues:
            if issue.get("enrolment_id"):
                flagged_enrolment_ids.add(str(issue["enrolment_id"]))
        for e in curr_enrolments:
            if e.get("validation_status") in ["WARNING", "ERROR"]:
                flagged_enrolment_ids.add(str(e.get("id")))
        warning_record_share = round(
            len(flagged_enrolment_ids) / max(total_curr_enrolments, 1), 4
        )

        # 5. APAAR failure share
        apaar_failures = 0
        surnames: List[str] = []
        dobs: List[str] = []

        for e in curr_enrolments:
            st = student_map.get(str(e.get("student_id")), {})
            apaar_id = e.get("apaar_id") or st.get("apaar_id")
            apaar_status = e.get("apaar_status") or st.get("apaar_status", "UNVERIFIED")

            if not apaar_id or apaar_status in ["NOT_FOUND", "MISMATCH", "UNVERIFIED"]:
                apaar_failures += 1

            # Surnames for entropy
            name = st.get("name") or st.get("name_enc") or ""
            parts = name.strip().split()
            if parts:
                surnames.append(parts[-1].lower())

            # DOBs for repeat ratio
            dob_val = st.get("dob") or st.get("dob_enc")
            if dob_val:
                dobs.append(str(dob_val))

        apaar_failure_share = round(
            apaar_failures / max(total_curr_enrolments, 1), 4
        )

        # 6. Admission burst index (max admissions on a single date / total)
        admission_dates = [
            str(e.get("admission_date") or e.get("created_at") or "")[:10]
            for e in curr_enrolments
            if e.get("admission_date") or e.get("created_at")
        ]
        if admission_dates:
            date_counts = Counter(admission_dates)
            max_single_day = max(date_counts.values())
            admission_burst_index = round(max_single_day / max(total_curr_enrolments, 1), 4)
        else:
            admission_burst_index = 0.0

        # 7. Exact intake match frequency
        exact_matches = 0
        program_enrolment_counts = Counter(str(e.get("program_id")) for e in curr_enrolments)
        valid_programs = [p for p in programs if p.get("approved_intake", 0) > 0]
        if valid_programs:
            for p in valid_programs:
                actual = program_enrolment_counts.get(str(p.get("id")), 0)
                if actual == p["approved_intake"]:
                    exact_matches += 1
            exact_intake_match_freq = round(exact_matches / len(valid_programs), 4)
        else:
            exact_intake_match_freq = 0.0

        # 8. Surname entropy
        if surnames:
            surname_entropy = compute_shannon_entropy(surnames)
        else:
            surname_entropy = 0.0

        # 9. DOB repeat ratio
        if dobs:
            unique_dobs = len(set(dobs))
            dob_repeat_ratio = round(1.0 - (unique_dobs / len(dobs)), 4)
        else:
            dob_repeat_ratio = 0.0

        return {
            "enrolment_to_intake_ratio": enrolment_to_intake_ratio,
            "yoy_enrolment_growth": yoy_enrolment_growth,
            "supernumerary_quota_share": supernumerary_quota_share,
            "warning_record_share": warning_record_share,
            "apaar_failure_share": apaar_failure_share,
            "admission_burst_index": admission_burst_index,
            "exact_intake_match_freq": exact_intake_match_freq,
            "surname_entropy": surname_entropy,
            "dob_repeat_ratio": dob_repeat_ratio,
        }

    @classmethod
    async def extract_for_all_institutions_async(
        cls,
        session: AsyncSession,
        academic_year: str = "2025-26",
    ) -> Dict[uuid.UUID, Dict[str, float]]:
        """Asynchronously extract features for all institutions in a given academic year from the database."""
        # Calculate prior academic year
        try:
            start_yr = int(academic_year.split("-")[0])
            prev_year = f"{start_yr - 1}-{str(start_yr)[2:]}"
        except Exception:
            prev_year = "2024-25"

        # 1. Fetch all institutions
        inst_res = await session.execute(select(Institution))
        institutions = list(inst_res.scalars().all())

        # 2. Fetch programs for this academic year
        prog_res = await session.execute(
            select(Program).where(Program.academic_year == academic_year)
        )
        programs = list(prog_res.scalars().all())
        prog_by_inst: Dict[uuid.UUID, List[Program]] = {i.id: [] for i in institutions}
        for p in programs:
            if p.institution_id in prog_by_inst:
                prog_by_inst[p.institution_id].append(p)

        # 3. Fetch enrolments with students for current year
        curr_enrol_res = await session.execute(
            select(Enrolment, Student)
            .join(Student, Enrolment.student_id == Student.id)
            .where(Enrolment.academic_year == academic_year)
        )
        curr_rows = curr_enrol_res.all()
        curr_enrol_by_inst: Dict[uuid.UUID, List[Enrolment]] = {i.id: [] for i in institutions}
        student_by_id: Dict[uuid.UUID, Student] = {}
        for en, st in curr_rows:
            curr_enrol_by_inst[en.institution_id].append(en)
            student_by_id[st.id] = st

        # 4. Fetch prior year enrolments for YoY growth
        prev_enrol_res = await session.execute(
            select(Enrolment.institution_id, func.count(Enrolment.id))
            .where(Enrolment.academic_year == prev_year)
            .group_by(Enrolment.institution_id)
        )
        prev_counts = dict(prev_enrol_res.all())

        # 5. Fetch validation issues counts per institution
        issue_res = await session.execute(
            select(ValidationIssue.institution_id, func.count(ValidationIssue.id))
            .group_by(ValidationIssue.institution_id)
        )
        issue_counts = dict(issue_res.all())

        results: Dict[uuid.UUID, Dict[str, float]] = {}

        for inst in institutions:
            inst_programs = prog_by_inst.get(inst.id, [])
            inst_enrolments = curr_enrol_by_inst.get(inst.id, [])
            total_curr = len(inst_enrolments)
            total_prev = prev_counts.get(inst.id, 0)

            approved_intake = sum(p.approved_intake for p in inst_programs)
            if approved_intake <= 0:
                approved_intake = inst.approved_total_intake

            # 1. Enrolment/intake ratio
            regular_active = [
                e for e in inst_enrolments
                if e.quota_type == "REGULAR" and not e.is_nri and not e.is_foreign_national and e.status == "ACTIVE"
            ]
            ratio = round(len(regular_active) / max(approved_intake, 1), 4)

            # 2. YoY growth
            if total_prev > 0:
                yoy = round((total_curr - total_prev) / total_prev, 4)
            else:
                yoy = 0.0

            # 3. Supernumerary share
            sup_count = sum(
                1 for e in inst_enrolments
                if e.quota_type in ["SUPERNUMERARY", "NRI", "FN", "OCI"] or e.is_nri or e.is_foreign_national
            )
            sup_share = round(sup_count / max(total_curr, 1), 4)

            # 4. Warning record share
            warn_count = issue_counts.get(inst.id, 0)
            warn_share = round(min(warn_count, total_curr) / max(total_curr, 1), 4)

            # 5. APAAR failures & demographics
            apaar_fail = 0
            surnames: List[str] = []
            dobs: List[str] = []
            admission_dates: List[str] = []

            for e in inst_enrolments:
                st = student_by_id.get(e.student_id)
                if not st or not st.apaar_id or st.apaar_status in ["NOT_FOUND", "MISMATCH", "UNVERIFIED"]:
                    apaar_fail += 1

                if st and st.name_enc:
                    parts = str(st.name_enc).strip().split()
                    if parts:
                        surnames.append(parts[-1].lower())

                if st and st.dob_enc:
                    dobs.append(str(st.dob_enc))

                if e.admission_date:
                    admission_dates.append(str(e.admission_date))

            apaar_share = round(apaar_fail / max(total_curr, 1), 4)

            # 6. Burst index
            if admission_dates:
                burst_val = max(Counter(admission_dates).values()) / max(total_curr, 1)
            else:
                burst_val = 0.0
            burst_index = round(burst_val, 4)

            # 7. Exact intake match
            prog_counts = Counter(e.program_id for e in inst_enrolments)
            valid_p = [p for p in inst_programs if p.approved_intake > 0]
            if valid_p:
                matches = sum(1 for p in valid_p if prog_counts.get(p.id, 0) == p.approved_intake)
                exact_freq = round(matches / len(valid_p), 4)
            else:
                exact_freq = 0.0

            # 8. Surname entropy
            entropy = compute_shannon_entropy(surnames) if surnames else 0.0

            # 9. DOB repeat ratio
            if dobs:
                dob_rep = round(1.0 - (len(set(dobs)) / len(dobs)), 4)
            else:
                dob_rep = 0.0

            results[inst.id] = {
                "enrolment_to_intake_ratio": ratio,
                "yoy_enrolment_growth": yoy,
                "supernumerary_quota_share": sup_share,
                "warning_record_share": warn_share,
                "apaar_failure_share": apaar_share,
                "admission_burst_index": burst_index,
                "exact_intake_match_freq": exact_freq,
                "surname_entropy": entropy,
                "dob_repeat_ratio": dob_rep,
            }

        return results
