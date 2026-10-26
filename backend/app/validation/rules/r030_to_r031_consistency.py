"""Rules R030 and R031: Demographic/Nationality Inconsistencies and Missing Quota Mandatory Fields."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.validation.base import BaseRule, RuleScope, RuleSeverity, RuleViolation, ValidationContext


class RuleR030InconsistentDemographics(BaseRule):
    """R030: Category, Nationality, OCI/NRI, and Age Inconsistencies."""
    code = "R030"
    name = "Demographic & Quota Inconsistencies"
    severity = RuleSeverity.ERROR
    scope = RuleScope.ROW
    description = (
        "Detects mutually exclusive demographic flags (FN with reservation, OCI+FN, NRI+FN, nationality mismatch), "
        "and implausible age or admission dates outside the academic session window."
    )
    remediation_hint = "Verify student passport, visa, caste certificate, and matriculation records, and adjust category flags."
    regulatory_ref = "AICTE Quota Eligibility Regulations & Citizenship Criteria Section 6"
    default_params = {
        "min_ug_age": 16,
        "max_ug_age": 70,
        "min_pg_age": 19,
        "max_pg_age": 70,
        "min_diploma_age": 14,
        "min_phd_age": 21,
    }

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []

        # Extract attributes from context (supports row record dictionary or ORM enrolment/student)
        rec = context.record or {}
        en = context.enrolment
        st = context.student
        prog = context.program

        is_fn = rec.get("is_foreign_national") if "is_foreign_national" in rec else (getattr(en, "is_foreign_national", False) if en else False)
        is_nri = rec.get("is_nri") if "is_nri" in rec else (getattr(en, "is_nri", False) if en else False)
        oci = rec.get("oci_status") if "oci_status" in rec else (getattr(en, "oci_status", False) if en else False)
        category = rec.get("admission_category") or (getattr(en, "admission_category", None) if en else None)
        nationality = (rec.get("nationality") or (getattr(en, "nationality", None) if en else "") or "INDIAN").strip().upper()
        admission_date_raw = rec.get("admission_date") or (getattr(en, "admission_date", None) if en else None)
        dob_raw = rec.get("dob") or (getattr(st, "dob_enc", None) if st else None)
        program_level = (rec.get("program_level") or rec.get("level") or (getattr(prog, "level", "UG") if prog else "UG")).upper()
        academic_year = rec.get("academic_year") or (getattr(en, "academic_year", None) if en else context.academic_year)

        inst_id = context.institution_id or (en.institution_id if en else uuid.uuid4())
        prog_id = context.program_id or (en.program_id if en else None)
        enrol_id = en.id if en else None

        # 1. Foreign National with Indian Reserved Category
        if is_fn and category and str(category).upper() in ("SC", "ST", "OBC", "EWS"):
            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message=f"Inconsistency: Foreign National student cannot claim Indian reserved category '{category}'.",
                    fields=["is_foreign_national", "admission_category"],
                    values={"is_foreign_national": True, "admission_category": category},
                    reason="Statutory reservation benefits (SC/ST/OBC/EWS) are strictly restricted to Indian citizens.",
                    extra_metadata={"subtype": "FN_WITH_INDIAN_RESERVED_CATEGORY"},
                )
            )

        # 2. OCI and Foreign National both marked
        if oci and is_fn:
            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message="Conflict: Student has both OCI (Overseas Citizen of India) and Foreign National flags marked.",
                    fields=["oci_status", "is_foreign_national"],
                    values={"oci_status": True, "is_foreign_national": True},
                    reason="OCI status is legally distinct from Foreign National quota under AICTE admission norms.",
                    extra_metadata={"subtype": "OCI_PLUS_FN_CONFLICT"},
                )
            )

        # 3. NRI and Foreign National both marked
        if is_nri and is_fn:
            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message="Conflict: Student has both Non-Resident Indian (NRI) and Foreign National flags marked.",
                    fields=["is_nri", "is_foreign_national"],
                    values={"is_nri": True, "is_foreign_national": True},
                    reason="NRI quota applies to Indian passport holders abroad; Foreign National quota is for non-citizens.",
                    extra_metadata={"subtype": "NRI_PLUS_FN_CONFLICT"},
                )
            )

        # 4. Foreign National with Nationality == INDIAN
        if is_fn and nationality == "INDIAN":
            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message="Inconsistency: Student marked as Foreign National but declared nationality is 'INDIAN'.",
                    fields=["is_foreign_national", "nationality"],
                    values={"is_foreign_national": True, "nationality": "INDIAN"},
                    reason="Foreign National candidates cannot have 'INDIAN' nationality.",
                    extra_metadata={"subtype": "FN_WITH_INDIAN_NATIONALITY"},
                )
            )

        # 5. Implausible Age at Admission
        if dob_raw:
            dob: Optional[date] = None
            if isinstance(dob_raw, (date, datetime)):
                dob = dob_raw.date() if isinstance(dob_raw, datetime) else dob_raw
            elif isinstance(dob_raw, str):
                try:
                    dob = date.fromisoformat(dob_raw.split("T")[0])
                except Exception:
                    pass

            adm_date: Optional[date] = None
            if isinstance(admission_date_raw, (date, datetime)):
                adm_date = admission_date_raw.date() if isinstance(admission_date_raw, datetime) else admission_date_raw
            elif isinstance(admission_date_raw, str):
                try:
                    adm_date = date.fromisoformat(admission_date_raw.split("T")[0])
                except Exception:
                    pass

            ref_date = adm_date or date(2025, 8, 1)
            if dob:
                age = ref_date.year - dob.year - ((ref_date.month, ref_date.day) < (dob.month, dob.day))

                min_age = self.params.get("min_ug_age", 16)
                max_age = self.params.get("max_ug_age", 70)
                if "PG" in program_level:
                    min_age = self.params.get("min_pg_age", 19)
                    max_age = self.params.get("max_pg_age", 70)
                elif "DIPLOMA" in program_level:
                    min_age = self.params.get("min_diploma_age", 14)
                elif "PHD" in program_level:
                    min_age = self.params.get("min_phd_age", 21)

                if age < min_age or age > max_age:
                    age_reason = f"Underage ({age} years < minimum {min_age} for {program_level})" if age < min_age else f"Overage ({age} years > maximum {max_age})"
                    violations.append(
                        self.build_violation(
                            institution_id=inst_id,
                            program_id=prog_id,
                            enrolment_id=enrol_id,
                            batch_id=context.batch_id,
                            message=f"Implausible age at admission: Student is {age} years old for {program_level} program ({age_reason}).",
                            fields=["dob", "admission_date"],
                            values={"dob": dob.isoformat(), "age": age, "program_level": program_level},
                            reason=f"Age at enrollment ({age} years) is outside plausible regulatory limits ({min_age}-{max_age} years).",
                            extra_metadata={"subtype": f"{'UNDERAGE' if age < min_age else 'OVERAGE'}_ADMISSION", "age": age},
                        )
                    )

        # 6. Admission Date Outside Academic Year Window
        if admission_date_raw and academic_year and "-" in str(academic_year):
            try:
                start_year = int(academic_year.split("-")[0])
                window_start = date(start_year, 4, 1)      # April 1 of start year
                window_end = date(start_year + 1, 3, 31)   # March 31 of next year

                adm_d: Optional[date] = None
                if isinstance(admission_date_raw, (date, datetime)):
                    adm_d = admission_date_raw.date() if isinstance(admission_date_raw, datetime) else admission_date_raw
                elif isinstance(admission_date_raw, str):
                    adm_d = date.fromisoformat(admission_date_raw.split("T")[0])

                if adm_d and (adm_d < window_start or adm_d > window_end):
                    violations.append(
                        self.build_violation(
                            institution_id=inst_id,
                            program_id=prog_id,
                            enrolment_id=enrol_id,
                            batch_id=context.batch_id,
                            message=f"Admission date {adm_d} is outside official academic session window for {academic_year} ({window_start} to {window_end}).",
                            fields=["admission_date", "academic_year"],
                            values={"admission_date": adm_d.isoformat(), "academic_year": academic_year},
                            reason=f"Enrollment date falls outside the permissible academic cycle window for session {academic_year}.",
                            severity_override=RuleSeverity.WARNING.value,
                            extra_metadata={"subtype": "ADMISSION_DATE_OUTSIDE_WINDOW"},
                        )
                    )
            except Exception:
                pass

        return violations


class RuleR031MissingMandatoryQuotaFields(BaseRule):
    """R031: Missing Mandatory Supporting Details for Special Quota Admissions."""
    code = "R031"
    name = "Missing Mandatory Quota Fields"
    severity = RuleSeverity.ERROR
    scope = RuleScope.ROW
    description = "Enforces that special admission categories (NRI, Foreign National, Supernumerary) supply required documentation fields."
    remediation_hint = "Upload authenticated sponsor affidavit, passport copy, and official quota entitlement proofs."
    regulatory_ref = "AICTE Quota Admission Verification Manual Section 7.2"

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        rec = context.record or {}
        en = context.enrolment

        quota_type = (rec.get("quota_type") or (getattr(en, "quota_type", None) if en else "") or "").upper()
        is_nri = rec.get("is_nri") if "is_nri" in rec else (getattr(en, "is_nri", False) if en else False)
        sponsor_details = rec.get("sponsor_details") or (getattr(en, "sponsor_details_enc", None) if en else None)
        is_fn = rec.get("is_foreign_national") if "is_foreign_national" in rec else (getattr(en, "is_foreign_national", False) if en else False)
        nationality = (rec.get("nationality") or (getattr(en, "nationality", None) if en else "") or "").strip().upper()

        inst_id = context.institution_id or (en.institution_id if en else uuid.uuid4())
        prog_id = context.program_id or (en.program_id if en else None)
        enrol_id = en.id if en else None

        # 1. NRI missing sponsor details
        nri_sponsor_missing = False
        if is_nri or quota_type == "NRI":
            if sponsor_details is None or str(sponsor_details).strip() in ("", "{}", "None"):
                nri_sponsor_missing = True
            elif isinstance(sponsor_details, dict):
                if not sponsor_details.get("sponsor_name") or not sponsor_details.get("sponsor_country"):
                    nri_sponsor_missing = True

        if nri_sponsor_missing:
            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message="NRI quota student is missing mandatory sponsor details / affidavit documentation.",
                    fields=["quota_type", "sponsor_details"],
                    values={"quota_type": "NRI", "sponsor_details": None},
                    reason="AICTE regulations require full authenticated sponsor relationship and financial details for NRI quota seats.",
                    extra_metadata={"subtype": "NRI_MISSING_SPONSOR_DETAILS"},
                )
            )

        # 2. TFW missing parental income
        if quota_type == "TFW":
            parental_income = rec.get("parental_income")
            if parental_income is None or str(parental_income).strip() in ("", "None"):
                violations.append(
                    self.build_violation(
                        institution_id=inst_id,
                        program_id=prog_id,
                        enrolment_id=enrol_id,
                        batch_id=context.batch_id,
                        message="TFW (Tuition Fee Waiver) quota student is missing mandatory parental income certificate.",
                        fields=["quota_type", "parental_income"],
                        values={"quota_type": "TFW", "parental_income": None},
                        reason="AICTE TFW scheme mandates parental annual income certificate below statutory ceiling (8 LPA).",
                        extra_metadata={"subtype": "TFW_MISSING_PARENTAL_INCOME"},
                    )
                )

        # 3. PMSSS missing allotment letter
        if quota_type == "PMSSS":
            allotment = rec.get("allotment_letter")
            if not allotment:
                violations.append(
                    self.build_violation(
                        institution_id=inst_id,
                        program_id=prog_id,
                        enrolment_id=enrol_id,
                        batch_id=context.batch_id,
                        message="PMSSS quota student is missing mandatory AICTE allotment letter documentation.",
                        fields=["quota_type", "allotment_letter"],
                        values={"quota_type": "PMSSS", "allotment_letter": None},
                        reason="PMSSS admissions require official AICTE central counseling allotment verification.",
                        extra_metadata={"subtype": "PMSSS_MISSING_ALLOTMENT"},
                    )
                )

        # 4. Foreign National missing passport/nationality
        if is_fn and (not nationality or nationality in ("INDIAN", "NONE", "UNKNOWN")):
            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message="Foreign National student is missing valid foreign country nationality / passport origin.",
                    fields=["is_foreign_national", "nationality"],
                    values={"is_foreign_national": True, "nationality": nationality or None},
                    reason="Foreign National quota seats require explicit declaration of sovereign foreign citizenship.",
                    extra_metadata={"subtype": "FN_MISSING_NATIONALITY"},
                )
            )

        return violations
