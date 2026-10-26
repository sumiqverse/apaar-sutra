"""Rules R001 to R004: APAAR Presence, Format, Registry Verification, and Demographic Matching."""

from typing import Any, Dict, List, Optional
import uuid

from app.validation.base import BaseRule, RuleScope, RuleSeverity, RuleViolation, ValidationContext
from app.validation.apaar_validator import validate_apaar, validate_verhoeff_checksum


class RuleR001MissingApaar(BaseRule):
    """R001: Missing APAAR ID."""
    code = "R001"
    name = "Missing APAAR ID"
    severity = RuleSeverity.ERROR
    scope = RuleScope.ROW
    description = "Checks that every student enrollment record contains a non-empty APAAR ID."
    remediation_hint = "Instruct candidate to create or retrieve their 12-digit APAAR ID via ABC / DigiLocker."
    regulatory_ref = "AICTE Approval Process Handbook (APH) 2024-27 Clause 3.1 & NEP 2020 Mandate"

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        raw_apaar = None
        if context.record:
            raw_apaar = context.record.get("apaar_id")
        elif context.student:
            raw_apaar = getattr(context.student, "apaar_id", None)

        if not raw_apaar or str(raw_apaar).strip() == "":
            inst_id = context.institution_id or (context.enrolment.institution_id if context.enrolment else uuid.uuid4())
            enrol_id = context.enrolment.id if context.enrolment else None
            prog_id = context.program_id or (context.enrolment.program_id if context.enrolment else None)

            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message="Student enrollment record is missing mandatory 12-digit APAAR identifier.",
                    fields=["apaar_id"],
                    values={"apaar_id": None},
                    reason="APAAR ID is mandatory for all students enrolled in AICTE-approved institutions under NEP 2020.",
                )
            )
        return violations


class RuleR002InvalidApaarFormat(BaseRule):
    """R002: Invalid APAAR Format or Mathematical Checksum Failure."""
    code = "R002"
    name = "Invalid APAAR Format"
    severity = RuleSeverity.ERROR
    scope = RuleScope.ROW
    description = "Validates length, digit composition, trivial repetition, and Verhoeff checksum algorithm."
    remediation_hint = "Re-verify student APAAR card or Aadhaar eKYC printout for transcription errors."
    regulatory_ref = "Ministry of Education APAAR Identifier Technical Specification v1.2"

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        raw_apaar = None
        if context.record:
            raw_apaar = context.record.get("apaar_id")
        elif context.student:
            raw_apaar = getattr(context.student, "apaar_id", None)

        if not raw_apaar or str(raw_apaar).strip() == "":
            return violations  # Handled by R001

        clean_id = str(raw_apaar).strip()
        val_res = validate_apaar(clean_id, enforce_checksum=True)

        if not val_res.is_valid:
            inst_id = context.institution_id or (context.enrolment.institution_id if context.enrolment else uuid.uuid4())
            enrol_id = context.enrolment.id if context.enrolment else None
            prog_id = context.program_id or (context.enrolment.program_id if context.enrolment else None)

            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message=f"APAAR ID format is invalid: {val_res.message}.",
                    fields=["apaar_id"],
                    values={"apaar_id": clean_id},
                    reason=f"Input failed national format or Verhoeff check digit validation: {val_res.message}.",
                    extra_metadata={"error_code": val_res.error_code, "severity": val_res.severity},
                )
            )
        return violations


class RuleR003ApaarNotFoundInRegistry(BaseRule):
    """R003: APAAR Not Found in National Registry."""
    code = "R003"
    name = "APAAR Not Found in Registry"
    severity = RuleSeverity.ERROR
    scope = RuleScope.ROW
    description = "Flags APAAR IDs that are syntactically valid but non-existent in the national ABC/DigiLocker registry."
    remediation_hint = "Ensure student's APAAR is synced on the national ABC / DigiLocker portal before finalizing enrollment."
    regulatory_ref = "Academic Bank of Credits (ABC) Operating Guidelines Section 4"

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        apaar_status = None
        raw_apaar = None
        if context.record:
            apaar_status = context.record.get("apaar_status")
            raw_apaar = context.record.get("apaar_id")
        elif context.student:
            apaar_status = getattr(context.student, "apaar_status", None)
            raw_apaar = getattr(context.student, "apaar_id", None)

        if str(apaar_status).upper() == "NOT_FOUND":
            inst_id = context.institution_id or (context.enrolment.institution_id if context.enrolment else uuid.uuid4())
            enrol_id = context.enrolment.id if context.enrolment else None
            prog_id = context.program_id or (context.enrolment.program_id if context.enrolment else None)
            clean_apaar = str(raw_apaar) if raw_apaar else "UNKNOWN"

            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message=f"APAAR ID {clean_apaar} was not found in the National Academic Registry.",
                    fields=["apaar_id", "apaar_status"],
                    values={"apaar_id": clean_apaar, "apaar_status": "NOT_FOUND"},
                    reason="The 12-digit APAAR ID does not exist in the National Academic Depository / ABC registry.",
                )
            )
        return violations


class RuleR004DemographicMismatch(BaseRule):
    """R004: Name/DOB Mismatch vs National Registry."""
    code = "R004"
    name = "Name/DOB Mismatch vs Registry"
    severity = RuleSeverity.WARNING
    scope = RuleScope.ROW
    description = "Detects discrepancies between institution-submitted student name/DOB and national registry records."
    remediation_hint = "Cross-check name spelling and date of birth against official Class X / matriculation certificate."
    regulatory_ref = "National Academic Depository Verification Guidelines Rule 7"
    default_params = {"min_name_match_score": 80}

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        apaar_status = None
        name_score = 100
        dob_match = True
        raw_apaar = None

        if context.record:
            apaar_status = context.record.get("apaar_status")
            name_score = context.record.get("name_match_score", 100)
            dob_match = context.record.get("dob_match", True)
            raw_apaar = context.record.get("apaar_id")
        elif context.student:
            apaar_status = getattr(context.student, "apaar_status", None)
            raw_apaar = getattr(context.student, "apaar_id", None)

        threshold = self.params.get("min_name_match_score", 80)
        is_mismatch = (
            str(apaar_status).upper() == "MISMATCH"
            or (name_score is not None and name_score < threshold)
            or dob_match is False
        )

        if is_mismatch:
            inst_id = context.institution_id or (context.enrolment.institution_id if context.enrolment else uuid.uuid4())
            enrol_id = context.enrolment.id if context.enrolment else None
            prog_id = context.program_id or (context.enrolment.program_id if context.enrolment else None)
            clean_apaar = str(raw_apaar) if raw_apaar else "UNKNOWN"

            violations.append(
                self.build_violation(
                    institution_id=inst_id,
                    program_id=prog_id,
                    enrolment_id=enrol_id,
                    batch_id=context.batch_id,
                    message=f"Demographic details for APAAR {clean_apaar} do not match the National Registry (Name match score: {name_score}%, DOB match: {dob_match}).",
                    fields=["name", "dob"],
                    values={"name_match_score": name_score, "dob_match": dob_match, "apaar_status": apaar_status},
                    reason=f"Demographic variance detected vs National Registry (Threshold: {threshold}%).",
                    extra_metadata={"name_score": name_score, "dob_match": dob_match},
                )
            )
        return violations
