"""Bulk student data ingestion service supporting streaming CSV/XLSX, idempotent upserts, and progress telemetry."""

import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Tuple
import uuid

import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import distinct, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.crypto import compute_blind_index, encrypt_field
from app.integrations.apaar import get_apaar_provider
from app.models.base import AsyncSessionLocal
from app.models.batch import UploadBatch
from app.models.enrolment import Enrolment, EnrolmentHistory
from app.models.program import Program
from app.models.student import Student
from app.models.validation import ValidationIssue
from app.validation.apaar_validator import normalize_apaar_id, validate_apaar

logger = logging.getLogger("bulk_ingestion_service")

# Template Headers matching full 21 fields
TEMPLATE_HEADERS = [
    "apaar_id",
    "student_ref_id",
    "name",
    "dob",
    "gender",
    "parent_name",
    "contact_email",
    "contact_phone",
    "program_name",
    "branch",
    "academic_year",
    "admission_category",
    "quota_type",
    "is_nri",
    "oci_status",
    "is_foreign_national",
    "nationality",
    "admission_date",
    "status",
]

SAMPLE_ROW = [
    "200000000013",
    "CS2025001",
    "Aarav Sharma",
    "2005-01-15",
    "MALE",
    "Rajesh Sharma",
    "aarav.sharma@example.edu.in",
    "9876543210",
    "B.Tech Computer Science",
    "CSE",
    "2025-26",
    "GEN",
    "REGULAR",
    "FALSE",
    "FALSE",
    "FALSE",
    "INDIAN",
    "2025-07-15",
    "ACTIVE",
]

DATA_DICTIONARY_ROWS = [
    ("apaar_id", "String (12 digits)", "Mandatory", "200000000013", "12-digit permanent academic identity number"),
    ("student_ref_id", "String (1-100)", "Mandatory", "CS2025001", "College roll number or institutional registration ID"),
    ("name", "String (1-150)", "Mandatory", "Aarav Sharma", "Full official legal name of student"),
    ("dob", "Date (YYYY-MM-DD)", "Mandatory", "2005-01-15", "Date of birth formatted as YYYY-MM-DD"),
    ("gender", "Enum", "Mandatory", "MALE", "Allowed values: MALE, FEMALE, OTHER"),
    ("parent_name", "String", "Optional", "Rajesh Sharma", "Father, mother, or guardian legal name"),
    ("contact_email", "Email", "Optional", "student@example.edu", "Student primary contact email"),
    ("contact_phone", "String (10-15)", "Optional", "9876543210", "10-digit mobile phone number"),
    ("program_name", "String", "Mandatory", "B.Tech Computer Science", "Degree program name matching approved program"),
    ("branch", "String", "Mandatory", "CSE", "Department branch code (e.g. CSE, ECE, MECH)"),
    ("academic_year", "String (YYYY-YY)", "Mandatory", "2025-26", "Academic batch year in YYYY-YY format"),
    ("admission_category", "Enum", "Mandatory", "GEN", "Category: GEN, EWS, OBC, SC, ST, PWD, OTHER"),
    ("quota_type", "Enum", "Mandatory", "REGULAR", "Quota: REGULAR, SUPERNUMERARY, NRI, OCI, FN, TFW, OTHER"),
    ("is_nri", "Boolean", "Optional", "FALSE", "TRUE if admitted under NRI category, else FALSE"),
    ("oci_status", "Boolean", "Optional", "FALSE", "Overseas Citizen of India status (TRUE/FALSE)"),
    ("is_foreign_national", "Boolean", "Optional", "FALSE", "Foreign national student flag (TRUE/FALSE)"),
    ("nationality", "String", "Optional", "INDIAN", "Country of citizenship (defaults to INDIAN)"),
    ("admission_date", "Date (YYYY-MM-DD)", "Mandatory", "2025-07-15", "Formal institutional admission date"),
    ("status", "Enum", "Mandatory", "ACTIVE", "Current enrolment status: ACTIVE, WITHDRAWN, COMPLETED"),
]


class BulkIngestionService:
    """Service orchestrating template generation, stream parsing, and worker ingestion."""

    @staticmethod
    def generate_template(file_format: str = "csv") -> Tuple[bytes, str]:
        """Generate sample template in CSV or rich XLSX with data validation and dictionaries."""
        clean_format = file_format.lower().strip()
        if clean_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(TEMPLATE_HEADERS)
            writer.writerow(SAMPLE_ROW)
            return output.getvalue().encode("utf-8-sig"), "text/csv"

        # XLSX with 3 worksheets
        wb = openpyxl.Workbook()
        
        # Sheet 1: Student Enrolment
        ws1 = wb.active
        ws1.title = "Student Enrolment"
        ws1.append(TEMPLATE_HEADERS)
        ws1.append(SAMPLE_ROW)

        # Apply dropdown validations in XLSX
        dv_gender = DataValidation(type="list", formula1='"MALE,FEMALE,OTHER"', allow_blank=False)
        ws1.add_data_validation(dv_gender)
        dv_gender.add("E2:E50000")

        dv_cat = DataValidation(type="list", formula1='"GEN,EWS,OBC,SC,ST,PWD,OTHER"', allow_blank=False)
        ws1.add_data_validation(dv_cat)
        dv_cat.add("L2:L50000")

        dv_quota = DataValidation(type="list", formula1='"REGULAR,SUPERNUMERARY,NRI,OCI,FN,TFW,OTHER"', allow_blank=False)
        ws1.add_data_validation(dv_quota)
        dv_quota.add("M2:M50000")

        dv_status = DataValidation(type="list", formula1='"ACTIVE,WITHDRAWN,COMPLETED"', allow_blank=False)
        ws1.add_data_validation(dv_status)
        dv_status.add("S2:S50000")

        # Sheet 2: Data Dictionary
        ws2 = wb.create_sheet(title="Data Dictionary")
        ws2.append(["Column Name", "Data Type", "Required", "Example Value", "Description & Constraints"])
        for row in DATA_DICTIONARY_ROWS:
            ws2.append(list(row))

        # Sheet 3: Program Intake Quota Declaration
        ws3 = wb.create_sheet(title="Program Quotas")
        ws3.append(["Program Name", "Level", "Branch", "Academic Year", "Approved Intake", "Supernumerary Seats", "Declared Enrolment"])
        ws3.append(["B.Tech Computer Science", "UG", "CSE", "2025-26", 60, 9, 65])

        out = io.BytesIO()
        wb.save(out)
        return out.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @staticmethod
    def stream_parse_file(file_path: str, chunk_size: int = 1000) -> Generator[List[Tuple[int, Dict[str, Any]]], None, None]:
        """Stream-parse CSV or XLSX file yielding chunks of (row_number, record_dict)."""
        ext = Path(file_path).suffix.lower()
        if ext == ".xlsx":
            yield from BulkIngestionService._stream_xlsx(file_path, chunk_size)
        else:
            yield from BulkIngestionService._stream_csv(file_path, chunk_size)

    @staticmethod
    def _stream_csv(file_path: str, chunk_size: int) -> Generator[List[Tuple[int, Dict[str, Any]]], None, None]:
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            # Sniff delimiter (comma, semicolon, tab)
            sample = f.read(4096)
            f.seek(0)
            delimiter = ","
            if sample:
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
                    delimiter = dialect.delimiter
                except Exception:
                    delimiter = ";" if ";" in sample and "," not in sample else ( "\t" if "\t" in sample else "," )

            reader = csv.reader(f, delimiter=delimiter)
            header_row = next(reader, None)
            if not header_row:
                return

            headers = [h.strip().lstrip("\ufeff").lower().replace(" ", "_") for h in header_row]

            chunk: List[Tuple[int, Dict[str, Any]]] = []
            row_idx = 1  # 1 is header
            for raw_row in reader:
                row_idx += 1
                if not raw_row or all(not str(c).strip() for c in raw_row):
                    continue  # skip blank lines

                record = {}
                for col_idx, col_name in enumerate(headers):
                    val = raw_row[col_idx].strip() if col_idx < len(raw_row) else ""
                    record[col_name] = val

                chunk.append((row_idx, record))
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []

            if chunk:
                yield chunk

    @staticmethod
    def _stream_xlsx(file_path: str, chunk_size: int) -> Generator[List[Tuple[int, Dict[str, Any]]], None, None]:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        # Choose "Student Enrolment" sheet or active
        ws = wb["Student Enrolment"] if "Student Enrolment" in wb.sheetnames else wb.active

        rows = ws.iter_rows(values_only=True)
        header_row = next(rows, None)
        if not header_row:
            wb.close()
            return

        headers = [str(h).strip().lower().replace(" ", "_") if h is not None else f"col_{i}" for i, h in enumerate(header_row)]

        chunk: List[Tuple[int, Dict[str, Any]]] = []
        row_idx = 1
        for raw_row in rows:
            row_idx += 1
            if not raw_row or all(c is None or str(c).strip() == "" for c in raw_row):
                continue

            record = {}
            for col_idx, col_name in enumerate(headers):
                val = raw_row[col_idx] if col_idx < len(raw_row) else ""
                # Excel date integer serial handling
                if isinstance(val, (datetime, date)):
                    record[col_name] = val.strftime("%Y-%m-%d")
                elif isinstance(val, (int, float)) and "dob" in col_name or "date" in col_name:
                    try:
                        dt = datetime(1899, 12, 30) + timedelta(days=int(val))
                        record[col_name] = dt.strftime("%Y-%m-%d")
                    except Exception:
                        record[col_name] = str(val).strip()
                elif val is not None:
                    record[col_name] = str(val).strip()
                else:
                    record[col_name] = ""

            chunk.append((row_idx, record))
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []

        if chunk:
            yield chunk
        wb.close()

    @staticmethod
    def parse_date(date_val: Any) -> Optional[date]:
        """Safely parse date from string or date/datetime object."""
        if not date_val:
            return None
        if isinstance(date_val, date) and not isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, datetime):
            return date_val.date()
        s = str(date_val).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s[:10], fmt).date()
            except ValueError:
                pass
        return None

    @staticmethod
    async def process_batch(
        batch_id: uuid.UUID,
        file_path: str,
        institution_id: uuid.UUID,
        session: AsyncSession,
        redis_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute stream-parsing and batch ingestion with APAAR validation and telemetry."""
        # 1. Fetch batch record
        batch = await session.get(UploadBatch, batch_id)
        if not batch:
            logger.error(f"Batch {batch_id} not found.")
            return {"status": "FAILED", "reason": "Batch not found"}

        batch.status = "PROCESSING"
        batch.started_at = datetime.now(timezone.utc)
        await session.commit()

        provider = get_apaar_provider()

        total_processed = 0
        total_accepted = 0
        total_warnings = 0
        total_rejected = 0

        # Pre-cache institution programs
        stmt = select(Program).where(Program.institution_id == institution_id)
        prog_res = await session.execute(stmt)
        programs_list = list(prog_res.scalars().all())
        programs_by_key = {
            (p.name.lower().strip(), p.branch.lower().strip(), p.academic_year): p
            for p in programs_list
        }

        # Progress update helper
        def update_redis_progress():
            if redis_client:
                try:
                    payload = json.dumps({
                        "batch_id": str(batch_id),
                        "status": "PROCESSING",
                        "processed": total_processed,
                        "accepted": total_accepted,
                        "warning": total_warnings,
                        "rejected": total_rejected,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    redis_client.set(f"batch:progress:{batch_id}", payload, ex=3600)
                except Exception:
                    pass

        # Stream file in chunks of 1000
        for chunk in BulkIngestionService.stream_parse_file(file_path, chunk_size=1000):
            # 1. Format check & prepare verification payload
            batch_verify_payload = []
            chunk_records_by_row = {}

            for row_idx, row in chunk:
                total_processed += 1
                raw_apaar = row.get("apaar_id", "")
                val_res = validate_apaar(raw_apaar)

                if not val_res.is_valid:
                    total_rejected += 1
                    issue = ValidationIssue(
                        id=uuid.uuid4(),
                        rule_code=val_res.error_code or "INVALID_APAAR_FORMAT",
                        severity="ERROR",
                        institution_id=institution_id,
                        batch_id=batch_id,
                        message=val_res.message,
                        explanation={
                            "row_number": row_idx,
                            "column": "apaar_id",
                            "value": raw_apaar,
                            "fix_hint": "Provide a valid 12-digit numeric APAAR ID without letters or special characters.",
                        },
                        status="OPEN",
                    )
                    session.add(issue)
                    continue

                clean_apaar = val_res.normalized_id
                parsed_dob = BulkIngestionService.parse_date(row.get("dob"))
                if not parsed_dob:
                    total_rejected += 1
                    issue = ValidationIssue(
                        id=uuid.uuid4(),
                        rule_code="INVALID_DOB_FORMAT",
                        severity="ERROR",
                        institution_id=institution_id,
                        batch_id=batch_id,
                        message=f"Date of birth '{row.get('dob')}' is not a valid date.",
                        explanation={
                            "row_number": row_idx,
                            "column": "dob",
                            "value": str(row.get("dob")),
                            "fix_hint": "Use ISO format YYYY-MM-DD (e.g. 2005-01-15).",
                        },
                        status="OPEN",
                    )
                    session.add(issue)
                    continue

                if val_res.severity == "WARNING":
                    total_warnings += 1
                    issue = ValidationIssue(
                        id=uuid.uuid4(),
                        rule_code=val_res.error_code or "APAAR_TRIVIAL_PATTERN",
                        severity="WARNING",
                        institution_id=institution_id,
                        batch_id=batch_id,
                        message=val_res.message,
                        explanation={
                            "row_number": row_idx,
                            "column": "apaar_id",
                            "value": clean_apaar,
                            "fix_hint": "Verify this is an authentic student APAAR credential and not a testing pattern.",
                        },
                        status="OPEN",
                    )
                    session.add(issue)

                # Queue for registry verification
                chunk_records_by_row[row_idx] = (row, clean_apaar, parsed_dob)
                batch_verify_payload.append({
                    "apaar_id": clean_apaar,
                    "name": row.get("name"),
                    "dob": parsed_dob,
                })

            # 2. Call provider batch verification
            ver_results = await provider.verify_batch(batch_verify_payload) if batch_verify_payload else {}

            # 3. Upsert valid rows
            for row_idx, (row, clean_apaar, parsed_dob) in chunk_records_by_row.items():
                ver_res = ver_results.get(clean_apaar)
                apaar_status = ver_res.status if ver_res else "PENDING"

                # Check if mismatch reported by registry
                if ver_res and ver_res.status == "MISMATCH":
                    total_warnings += 1
                    session.add(ValidationIssue(
                        id=uuid.uuid4(),
                        rule_code="APAAR_REGISTRY_MISMATCH",
                        severity="WARNING",
                        institution_id=institution_id,
                        batch_id=batch_id,
                        message=ver_res.reason or "Name or DOB mismatched with DigiLocker registry.",
                        explanation={
                            "row_number": row_idx,
                            "column": "name",
                            "value": row.get("name"),
                            "name_score": ver_res.name_match_score,
                            "fix_hint": "Verify demographic details against student's DigiLocker account.",
                        },
                        status="OPEN",
                    ))

                # Resolve Program
                prog_name = (row.get("program_name") or "General Program").strip()
                branch = (row.get("branch") or "General").strip()
                ay = (row.get("academic_year") or "2025-26").strip()

                prog = programs_by_key.get((prog_name.lower(), branch.lower(), ay))
                if not prog:
                    # Dynamically register program for institution
                    prog = Program(
                        id=uuid.uuid4(),
                        institution_id=institution_id,
                        name=prog_name,
                        level="UG",
                        branch=branch,
                        academic_year=ay,
                        approved_intake=60,
                        supernumerary_seats=0,
                        supernumerary_cap_pct=15.0,
                    )
                    session.add(prog)
                    await session.flush()
                    programs_by_key[(prog_name.lower(), branch.lower(), ay)] = prog

                # Query or Create Student
                st_query = select(Student).where(Student.apaar_id == clean_apaar)
                st_res = await session.execute(st_query)
                student = st_res.scalar_one_or_none()

                student_name = row.get("name", "Student").strip()
                parent_name = row.get("parent_name", "").strip() or None
                gender_clean = row.get("gender", "OTHER").upper().strip()
                if gender_clean not in ("MALE", "FEMALE", "OTHER"):
                    gender_clean = "OTHER"

                contact_dict = {
                    "email": row.get("contact_email", ""),
                    "phone": row.get("contact_phone", ""),
                }

                if not student:
                    student = Student(
                        id=uuid.uuid4(),
                        apaar_id=clean_apaar,
                        apaar_status=apaar_status,
                        name_enc=student_name,
                        dob_enc=parsed_dob,
                        gender=gender_clean,
                        parent_name_enc=parent_name,
                        contact_enc=contact_dict,
                        name_bidx=compute_blind_index(student_name),
                        dob_bidx=compute_blind_index(parsed_dob.isoformat()),
                        parent_bidx=compute_blind_index(parent_name) if parent_name else None,
                    )
                    session.add(student)
                    await session.flush()
                else:
                    # Update status
                    if apaar_status != "PENDING":
                        student.apaar_status = apaar_status

                # Idempotent Enrolment Check: (student_id, institution_id, program_id, academic_year)
                enrol_query = (
                    select(Enrolment)
                    .options(selectinload(Enrolment.history_entries))
                    .where(
                        Enrolment.student_id == student.id,
                        Enrolment.institution_id == institution_id,
                        Enrolment.program_id == prog.id,
                        Enrolment.academic_year == ay,
                    )
                )
                enrol_res = await session.execute(enrol_query)
                enrol = enrol_res.scalar_one_or_none()

                ref_id = row.get("student_ref_id", f"REF-{clean_apaar[-6:]}").strip()
                adm_date = BulkIngestionService.parse_date(row.get("admission_date")) or date.today()
                cat = row.get("admission_category", "GEN").upper().strip()
                quota = row.get("quota_type", "REGULAR").upper().strip()
                is_nri_val = str(row.get("is_nri", "false")).lower() in ("true", "1", "yes")
                oci_val = str(row.get("oci_status", "false")).lower() in ("true", "1", "yes")
                fn_val = str(row.get("is_foreign_national", "false")).lower() in ("true", "1", "yes")
                nat = row.get("nationality", "INDIAN").strip()
                st_val = row.get("status", "ACTIVE").upper().strip()

                if not enrol:
                    # New Enrolment
                    enrol = Enrolment(
                        id=uuid.uuid4(),
                        student_id=student.id,
                        institution_id=institution_id,
                        program_id=prog.id,
                        academic_year=ay,
                        student_ref_id=ref_id,
                        admission_category=cat if cat in ("GEN", "EWS", "OBC", "SC", "ST", "PWD", "OTHER") else "GEN",
                        quota_type=quota if quota in ("REGULAR", "SUPERNUMERARY", "NRI", "OCI", "FN", "TFW", "OTHER") else "REGULAR",
                        is_nri=is_nri_val,
                        oci_status=oci_val,
                        is_foreign_national=fn_val,
                        nationality=nat or "INDIAN",
                        admission_date=adm_date,
                        status=st_val if st_val in ("ACTIVE", "WITHDRAWN", "COMPLETED") else "ACTIVE",
                        source_batch_id=batch_id,
                    )
                    session.add(enrol)
                    await session.flush()

                    # Add history
                    history = EnrolmentHistory(
                        id=uuid.uuid4(),
                        enrolment_id=enrol.id,
                        changed_by=batch.uploaded_by,
                        action="CREATE",
                        diff={"initial_import": True, "batch_id": str(batch_id)},
                    )
                    session.add(history)
                    total_accepted += 1
                else:
                    # Idempotent re-upload: detect diffs
                    diff = {}
                    if enrol.student_ref_id != ref_id:
                        diff["student_ref_id"] = {"old": enrol.student_ref_id, "new": ref_id}
                        enrol.student_ref_id = ref_id
                    if enrol.status != st_val and st_val in ("ACTIVE", "WITHDRAWN", "COMPLETED"):
                        diff["status"] = {"old": enrol.status, "new": st_val}
                        enrol.status = st_val
                    if enrol.admission_category != cat and cat in ("GEN", "EWS", "OBC", "SC", "ST", "PWD", "OTHER"):
                        diff["admission_category"] = {"old": enrol.admission_category, "new": cat}
                        enrol.admission_category = cat
                    if enrol.quota_type != quota and quota in ("REGULAR", "SUPERNUMERARY", "NRI", "OCI", "FN", "TFW", "OTHER"):
                        diff["quota_type"] = {"old": enrol.quota_type, "new": quota}
                        enrol.quota_type = quota

                    if diff:
                        history = EnrolmentHistory(
                            id=uuid.uuid4(),
                            enrolment_id=enrol.id,
                            changed_by=batch.uploaded_by,
                            action="UPDATE",
                            diff=diff,
                        )
                        session.add(history)

                    enrol.source_batch_id = batch_id
                    total_accepted += 1

            # Commit chunk
            await session.commit()
            update_redis_progress()

        # Finalize batch telemetry
        batch.total_rows = total_processed
        batch.processed_rows = total_processed
        batch.accepted_rows = total_accepted
        batch.warning_rows = total_warnings
        batch.rejected_rows = total_rejected
        batch.status = "COMPLETED"
        batch.finished_at = datetime.now(timezone.utc)
        await session.commit()

        if redis_client:
            try:
                payload = json.dumps({
                    "batch_id": str(batch_id),
                    "status": "COMPLETED",
                    "processed": total_processed,
                    "accepted": total_accepted,
                    "warning": total_warnings,
                    "rejected": total_rejected,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                redis_client.set(f"batch:progress:{batch_id}", payload, ex=86400)
            except Exception:
                pass

        logger.info(f"Batch {batch_id} completed: {total_accepted} accepted, {total_warnings} warnings, {total_rejected} rejected.")
        return {
            "batch_id": str(batch_id),
            "status": "COMPLETED",
            "total_rows": total_processed,
            "accepted_rows": total_accepted,
            "warning_rows": total_warnings,
            "rejected_rows": total_rejected,
        }

    @staticmethod
    async def get_batch_errors(session: AsyncSession, batch_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Retrieve all structured validation issues recorded for a batch."""
        stmt = (
            select(ValidationIssue)
            .where(ValidationIssue.batch_id == batch_id)
            .order_by(ValidationIssue.created_at.asc())
        )
        res = await session.execute(stmt)
        issues = res.scalars().all()

        results = []
        for iss in issues:
            exp = iss.explanation or {}
            results.append({
                "row_number": exp.get("row_number", 0),
                "column": exp.get("column", ""),
                "value": exp.get("value", ""),
                "error_code": iss.rule_code,
                "reason": iss.message,
                "fix_hint": exp.get("fix_hint", "Verify field value conforms to data dictionary."),
            })
        return results
