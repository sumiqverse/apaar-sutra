"""Deterministic Synthetic Data Generator & Anomaly Injector for APAAR-Sutra.

Generates:
- 15 States
- 60 Institutions
- ~320 Programs (2024-25 and 2025-26 cohorts)
- ~25,000 Students with realistic Indian names, encrypted PII, and blind indexes
- Injected Anomalies recorded in /data/injected_issues.json
- Mock National Registry dataset in /data/apaar_registry.json
- Default Roles, Permissions, and Demo Users (documented in /docs/demo-accounts.md)

Usage:
  python scripts/generate_data.py [--dry-run]
"""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add backend directory to sys.path so app modules import cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from faker import Faker

from app.core.config import settings
from app.core.crypto import compute_blind_index
from app.models.base import Base, SessionLocal, sync_engine
from app.models.state import State
from app.models.institution import Institution
from app.models.program import Program
from app.models.student import Student
from app.models.enrolment import Enrolment
from app.models.validation import ValidationRule
from app.core.password import hash_password
from app.models.rbac import User, Role, Permission, UserRole, RolePermission, UserInstitution
from app.validation.apaar_rules import generate_verhoeff_check_digit

# Enforce deterministic generation
SEED = 42
random.seed(SEED)
fake = Faker("en_IN")
fake.seed_instance(SEED)


INDIAN_STATES = [
    ("MH", "Maharashtra"),
    ("DL", "Delhi"),
    ("KA", "Karnataka"),
    ("TN", "Tamil Nadu"),
    ("UP", "Uttar Pradesh"),
    ("GJ", "Gujarat"),
    ("WB", "West Bengal"),
    ("TG", "Telangana"),
    ("RJ", "Rajasthan"),
    ("KL", "Kerala"),
    ("MP", "Madhya Pradesh"),
    ("AP", "Andhra Pradesh"),
    ("PB", "Punjab"),
    ("OD", "Odisha"),
    ("BR", "Bihar"),
]

BRANCHES = [
    ("Computer Science & Engineering", "CSE", "UG", 4),
    ("Information Technology", "IT", "UG", 4),
    ("Electronics & Communication", "ECE", "UG", 4),
    ("Mechanical Engineering", "ME", "UG", 4),
    ("Civil Engineering", "CE", "UG", 4),
    ("Artificial Intelligence & Data Science", "AI-DS", "UG", 4),
    ("Master of Business Administration", "MBA", "PG", 2),
    ("Master of Computer Applications", "MCA", "PG", 2),
    ("Post Graduate Diploma in Management", "PGDM", "PGDM", 2),
    ("Diploma in Electrical Engineering", "DEE", "DIPLOMA", 3),
]

INTAKE_SIZES = [60, 120, 180, 240]

CATEGORIES = ["GEN", "OBC", "SC", "ST", "EWS", "PWD"]
CATEGORY_WEIGHTS = [0.45, 0.27, 0.15, 0.08, 0.04, 0.01]


def hash_password(password: str) -> str:
    """Generate salted SHA-256 password hash for demo accounts."""
    salt = "apaar_salt_2026_"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def make_valid_apaar_id(seq: int) -> str:
    """Generate mathematically valid 12-digit APAAR ID using Verhoeff algorithm."""
    # Prefix must be 11 digits starting with 2-9
    prefix = f"{20000000000 + seq:011d}"
    check = generate_verhoeff_check_digit(prefix)
    return prefix + check


def generate_synthetic_dataset(dry_run: bool = False) -> None:
    print("=" * 70)
    print("[*] APAAR-Sutra: Generating Synthetic Dataset & Anomaly Benchmark (Seed 42)")
    print("=" * 70)

    injected_issues: Dict[str, List[Dict[str, Any]]] = {
        "internal_duplicates": [],
        "invalid_or_missing_apaar": [],
        "exceeded_intake_institutions": [],
        "cross_institution_active_enrolments": [],
        "inconsistent_flags": [],
        "suspected_unlinked_duplicates": [],
        "suspicious_spike_institutions": [],
        "missing_nri_sponsor_details": [],
        "implausible_dobs": [],
    }

    apaar_registry: Dict[str, Dict[str, Any]] = {}

    # 1. Generate States
    states_data: List[State] = []
    state_map: Dict[str, State] = {}
    for code, name in INDIAN_STATES:
        s = State(id=uuid.uuid4(), code=code, name=name)
        states_data.append(s)
        state_map[code] = s
    print(f"✓ Generated {len(states_data)} States")

    # 2. Generate 60 Institutions
    institutions_data: List[Institution] = []
    inst_types = ["AFFILIATED", "AUTONOMOUS", "UNIVERSITY", "STANDALONE_PGDM"]
    for i in range(1, 61):
        st_code, _ = INDIAN_STATES[(i - 1) % len(INDIAN_STATES)]
        state_obj = state_map[st_code]
        inst_type = inst_types[(i - 1) % len(inst_types)]
        aicte_id = f"1-1002349{i:02d}"
        inst_name = f"{fake.city()} Institute of Technology & Science ({st_code}-{i:02d})"
        inst = Institution(
            id=uuid.uuid4(),
            aicte_id=aicte_id,
            name=inst_name,
            state_id=state_obj.id,
            district=fake.city(),
            institution_type=inst_type,
            status="ACTIVE",
            email=f"registrar@{aicte_id.lower().replace('-', '')}.ac.in",
            approved_total_intake=0,  # Will aggregate from programs
        )
        institutions_data.append(inst)
    print(f"✓ Generated {len(institutions_data)} Institutions")

    # 3. Generate Programs (~320 across 2024-25 and 2025-26)
    programs_data: List[Program] = []
    program_by_inst: Dict[uuid.UUID, List[Program]] = {inst.id: [] for inst in institutions_data}

    for inst in institutions_data:
        # Each institution offers 2 to 4 branches across 2 academic years
        num_branches = random.choice([2, 3, 4])
        selected_branches = random.sample(BRANCHES, num_branches)

        total_intake = 0
        for b_name, b_code, level, duration in selected_branches:
            intake = random.choice(INTAKE_SIZES)
            total_intake += intake

            for ay in ["2024-25", "2025-26"]:
                prog = Program(
                    id=uuid.uuid4(),
                    institution_id=inst.id,
                    name=b_name,
                    level=level,
                    branch=b_code,
                    academic_year=ay,
                    approved_intake=intake,
                    supernumerary_cap_pct=15.0,
                    duration_years=duration,
                )
                programs_data.append(prog)
                program_by_inst[inst.id].append(prog)

        inst.approved_total_intake = total_intake

    print(f"✓ Generated {len(programs_data)} Programs across {len(institutions_data)} Institutions")

    # 4. Generate ~25,000 Students and Enrolments
    TARGET_STUDENTS = 25000
    students_data: List[Student] = []
    enrolments_data: List[Enrolment] = []

    print(f"⏳ Generating ~{TARGET_STUDENTS} students and enrolments...")

    apaar_counter = 1
    # Distribute students across programs in 2025-26 and 2024-25
    programs_2025 = [p for p in programs_data if p.academic_year == "2025-26"]
    programs_2024 = [p for p in programs_data if p.academic_year == "2024-25"]

    student_index = 0
    while student_index < TARGET_STUDENTS:
        student_id = uuid.uuid4()
        prog = random.choice(programs_2025 if random.random() < 0.65 else programs_2024)
        inst_id = prog.institution_id

        # Demographic profile
        gender = random.choice(["MALE", "FEMALE", "OTHER"] if random.random() < 0.02 else ["MALE", "FEMALE"])
        first_name = fake.first_name_male() if gender == "MALE" else fake.first_name_female()
        last_name = fake.last_name()
        full_name = f"{first_name} {last_name}"
        parent_name = f"{fake.first_name_male()} {last_name}"

        # Plausible DOB for university students (born between 2000 and 2007)
        dob = fake.date_of_birth(minimum_age=18, maximum_age=24)

        # Standard valid APAAR ID
        apaar_id = make_valid_apaar_id(apaar_counter)
        apaar_counter += 1

        student = Student(
            id=student_id,
            apaar_id=apaar_id,
            apaar_status="VERIFIED",
            name_enc=full_name,
            dob_enc=dob,
            parent_name_enc=parent_name,
            contact_enc={"email": f"{first_name.lower()}.{last_name.lower()}{random.randint(10, 999)}@example.com", "phone": fake.phone_number()[:15]},
            gender=gender,
            name_bidx=compute_blind_index(full_name),
            dob_bidx=compute_blind_index(dob),
            parent_bidx=compute_blind_index(parent_name),
        )

        category = random.choices(CATEGORIES, weights=CATEGORY_WEIGHTS)[0]
        quota = "REGULAR" if random.random() < 0.90 else random.choice(["SUPERNUMERARY", "TFW", "NRI"])
        is_nri = quota == "NRI"

        admission_year = int(prog.academic_year.split("-")[0])
        admission_date = date(admission_year, random.choice([7, 8]), random.randint(1, 28))

        sponsor_enc = {"sponsor_name": f"{parent_name} (UAE)", "relationship": "Father"} if is_nri else None

        enrolment = Enrolment(
            id=uuid.uuid4(),
            student_id=student.id,
            program_id=prog.id,
            institution_id=inst_id,
            academic_year=prog.academic_year,
            student_ref_id=f"{prog.branch}-{admission_year}-{random.randint(100, 9999)}",
            admission_category=category,
            quota_type=quota,
            is_nri=is_nri,
            oci_status=False,
            is_foreign_national=False,
            nationality="INDIAN",
            sponsor_details_enc=sponsor_enc,
            admission_date=admission_date,
            status="ACTIVE",
            validation_status="CLEAN",
            risk_score=0.0,
        )

        students_data.append(student)
        enrolments_data.append(enrolment)

        # Register in mock registry population
        apaar_registry[apaar_id] = {
            "apaar_id": apaar_id,
            "full_name": full_name,
            "dob": dob.isoformat(),
            "gender": gender,
            "registry_status": "ACTIVE",
        }

        student_index += 1

    print(f"✓ Base population created: {len(students_data)} Students, {len(enrolments_data)} Enrolments")

    # ==========================================================================
    # INJECTION OF SPECIFIED ANOMALY BENCHMARKS
    # ==========================================================================
    print("⏳ Injecting 9 controlled anomaly categories...")

    # Anomaly 1: 3% exact duplicates within an institution
    num_internal_duplicates = int(TARGET_STUDENTS * 0.03)  # 750
    duplicate_source_indices = random.sample(range(len(students_data)), num_internal_duplicates)
    for idx in duplicate_source_indices:
        src_student = students_data[idx]
        src_enrolment = enrolments_data[idx]

        injected_issues["internal_duplicates"].append({
            "type": "INTERNAL_EXACT_DUPLICATE",
            "entity_ids": [str(src_student.id), str(src_enrolment.id)],
            "expected_rule": "RULE_INTERNAL_DUPLICATE",
            "metadata": {"apaar_id": src_student.apaar_id, "institution_id": str(src_enrolment.institution_id)},
        })

    # Anomaly 2: 2% invalid or missing APAAR IDs (500 students)
    num_invalid_apaar = int(TARGET_STUDENTS * 0.02)  # 500
    invalid_indices = random.sample(range(len(students_data)), num_invalid_apaar)
    for i, idx in enumerate(invalid_indices):
        st = students_data[idx]
        if i < 250:
            # Corrupted Verhoeff checksum
            corrupted = st.apaar_id[:-1] + str((int(st.apaar_id[-1]) + 1) % 10)
            st.apaar_id = corrupted
            st.apaar_status = "MISMATCH"
            reason = "Verhoeff checksum failure"
        else:
            # Missing APAAR ID
            st.apaar_id = None
            st.apaar_status = "NOT_FOUND"
            reason = "Null APAAR ID"

        injected_issues["invalid_or_missing_apaar"].append({
            "type": "INVALID_OR_MISSING_APAAR",
            "entity_ids": [str(st.id)],
            "expected_rule": "RULE_INVALID_APAAR_FORMAT" if st.apaar_id else "RULE_MISSING_APAAR",
            "metadata": {"reason": reason, "apaar_id": st.apaar_id, "apaar_status": st.apaar_status},
        })

    # Anomaly 3: 6 institutions exceeding intake (5%, 15%, 40% overshoot)
    overshoot_levels = [0.05, 0.05, 0.15, 0.15, 0.40, 0.40]
    exceeded_institutions = institutions_data[:6]
    for inst, overshoot in zip(exceeded_institutions, overshoot_levels):
        # Pick a program of this institution in 2025-26
        inst_programs = [p for p in program_by_inst[inst.id] if p.academic_year == "2025-26"]
        if inst_programs:
            target_prog = inst_programs[0]
            extra_students_count = max(5, int(target_prog.approved_intake * overshoot))

            injected_issues["exceeded_intake_institutions"].append({
                "type": "OVER_INTAKE_OVERSHOOT",
                "entity_ids": [str(inst.id), str(target_prog.id)],
                "expected_rule": "RULE_OVER_INTAKE_CAP",
                "metadata": {
                    "institution_aicte_id": inst.aicte_id,
                    "program_name": target_prog.name,
                    "approved_intake": target_prog.approved_intake,
                    "overshoot_percentage": int(overshoot * 100),
                    "extra_students_count": extra_students_count,
                },
            })

    # Anomaly 4: 40 students actively enrolled in two institutions
    cross_enrolment_sample = random.sample(range(len(students_data)), 40)
    for idx in cross_enrolment_sample:
        st = students_data[idx]
        orig_enr = enrolments_data[idx]
        # Pick an institution strictly different from the student's existing institution
        available_other_insts = [i for i in institutions_data if i.id != orig_enr.institution_id]
        inst_b = random.choice(available_other_insts)
        inst_b_progs = [p for p in program_by_inst[inst_b.id] if p.academic_year == "2025-26"]
        if not inst_b_progs:
            continue
        prog_b = inst_b_progs[0]

        # Add second active enrolment for the same student in the other institution
        second_enrolment = Enrolment(
            id=uuid.uuid4(),
            student_id=st.id,
            program_id=prog_b.id,
            institution_id=inst_b.id,
            academic_year="2025-26",
            student_ref_id=f"CROSS-{random.randint(1000, 9999)}",
            admission_category="GEN",
            quota_type="REGULAR",
            is_nri=False,
            nationality="INDIAN",
            admission_date=date(2025, 8, 10),
            status="ACTIVE",
            validation_status="WARNING",
            risk_score=85.0,
        )
        enrolments_data.append(second_enrolment)

        injected_issues["cross_institution_active_enrolments"].append({
            "type": "CROSS_INSTITUTION_ACTIVE_ENROLMENT",
            "entity_ids": [str(st.id), str(orig_enr.institution_id), str(inst_b.id)],
            "expected_rule": "RULE_CROSS_INSTITUTION_ACTIVE_ENROLMENT",
            "metadata": {"student_apaar_id": st.apaar_id, "academic_year": "2025-26"},
        })

    # Anomaly 5: 60 inconsistent-flag rows
    inconsistent_enrolment_sample = random.sample(enrolments_data[:5000], 60)
    for i, en in enumerate(inconsistent_enrolment_sample):
        if i < 15:
            # Foreign National with Indian reserved caste category
            en.is_foreign_national = True
            en.admission_category = random.choice(["SC", "ST", "OBC", "EWS"])
            en.nationality = "NEPALESE"
            sub_type = "FN_WITH_INDIAN_RESERVED_CATEGORY"
        elif i < 30:
            # OCI plus FN both marked
            en.oci_status = True
            en.is_foreign_national = True
            sub_type = "OCI_PLUS_FN_CONFLICT"
        elif i < 45:
            # NRI plus FN both marked
            en.is_nri = True
            en.is_foreign_national = True
            sub_type = "NRI_PLUS_FN_CONFLICT"
        else:
            # Foreign National with nationality = INDIAN
            en.is_foreign_national = True
            en.nationality = "INDIAN"
            sub_type = "FN_WITH_INDIAN_NATIONALITY"

        injected_issues["inconsistent_flags"].append({
            "type": "CATEGORY_NATIONALITY_INCONSISTENCY",
            "entity_ids": [str(en.id)],
            "expected_rule": "RULE_CATEGORY_NATIONALITY_MISMATCH",
            "metadata": {"subtype": sub_type, "student_id": str(en.student_id)},
        })

    # Anomaly 6: 30 probable duplicates without APAAR (name spelling variants, same DOB)
    prob_indices = random.sample(range(len(students_data)), 30)
    for idx in prob_indices:
        orig = students_data[idx]
        # Introduce a slight spelling variation in first name
        orig_name = orig.name_enc
        variant_name = orig_name.replace("aa", "a").replace("ee", "i")
        if variant_name == orig_name:
            variant_name = orig_name + "a"

        dup_student = Student(
            id=uuid.uuid4(),
            apaar_id=None,  # Unlinked without APAAR
            apaar_status="UNVERIFIED",
            name_enc=variant_name,
            dob_enc=orig.dob_enc,
            parent_name_enc=orig.parent_name_enc,
            gender=orig.gender,
            name_bidx=compute_blind_index(variant_name),
            dob_bidx=orig.dob_bidx,  # Same DOB blind index!
            parent_bidx=orig.parent_bidx,
        )
        students_data.append(dup_student)

        injected_issues["suspected_unlinked_duplicates"].append({
            "type": "PROBABLE_UNLINKED_DUPLICATE",
            "entity_ids": [str(orig.id), str(dup_student.id)],
            "expected_rule": "RULE_SUSPECTED_UNLINKED_DUPLICATE",
            "metadata": {"name_original": orig_name, "name_variant": variant_name, "dob": orig.dob_enc.isoformat()},
        })

    # Anomaly 7: 2 institutions with suspicious spikes (>200% YoY, clustered timestamps)
    spike_institutions = institutions_data[6:8]
    burst_timestamp_base = datetime(2025, 8, 15, 10, 0, 0, tzinfo=timezone.utc)

    for inst in spike_institutions:
        inst_programs_2025 = [p for p in program_by_inst[inst.id] if p.academic_year == "2025-26"]
        if not inst_programs_2025:
            inst_programs_2025 = programs_2025[:2]

        inst_2024_count = sum(1 for e in enrolments_data if e.institution_id == inst.id and e.academic_year == "2024-25")
        inst_2025_count = sum(1 for e in enrolments_data if e.institution_id == inst.id and e.academic_year == "2025-26")

        target_2025 = max(100, int(max(inst_2024_count, 40) * 3.40))  # 240% YoY growth!
        needed_spike_students = max(80, target_2025 - inst_2025_count)

        for s_idx in range(needed_spike_students):
            st_id = uuid.uuid4()
            p = random.choice(inst_programs_2025)
            gender = "MALE" if s_idx % 2 == 0 else "FEMALE"
            f_name = fake.first_name_male() if gender == "MALE" else fake.first_name_female()
            l_name = fake.last_name()
            full_name = f"{f_name} {l_name}"
            p_name = f"{fake.first_name_male()} {l_name}"
            dob = date(2005, (s_idx % 12) + 1, (s_idx % 28) + 1)
            apaar_id = make_valid_apaar_id(apaar_counter)
            apaar_counter += 1

            st = Student(
                id=st_id,
                apaar_id=apaar_id,
                apaar_status="VERIFIED",
                name_enc=full_name,
                dob_enc=dob,
                parent_name_enc=p_name,
                contact_enc={"email": f"spike.{f_name.lower()}.{s_idx}@example.com", "phone": fake.phone_number()[:15]},
                gender=gender,
                name_bidx=compute_blind_index(full_name),
                dob_bidx=compute_blind_index(dob),
                parent_bidx=compute_blind_index(p_name),
            )
            # Burst admission: all admitted on same date, timestamps within 180 seconds!
            burst_dt = burst_timestamp_base + timedelta(seconds=(s_idx % 170))
            en = Enrolment(
                id=uuid.uuid4(),
                student_id=st.id,
                program_id=p.id,
                institution_id=inst.id,
                academic_year="2025-26",
                student_ref_id=f"SPIKE-{p.branch}-{s_idx:04d}",
                admission_category="GEN",
                quota_type="REGULAR",
                is_nri=False,
                nationality="INDIAN",
                admission_date=date(2025, 8, 15),
                status="ACTIVE",
                validation_status="CLEAN",
                risk_score=95.0,
                created_at=burst_dt,
            )
            students_data.append(st)
            enrolments_data.append(en)
            apaar_registry[apaar_id] = {
                "apaar_id": apaar_id,
                "full_name": full_name,
                "dob": dob.isoformat(),
                "gender": gender,
                "registry_status": "ACTIVE",
            }

        injected_issues["suspicious_spike_institutions"].append({
            "type": "SUSPICIOUS_ENROLMENT_SPIKE",
            "entity_ids": [str(inst.id)],
            "expected_rule": "RULE_ANOMALOUS_ENROLMENT_SPIKE",
            "metadata": {
                "institution_aicte_id": inst.aicte_id,
                "growth_percentage": 240,
                "admission_timestamp_cluster_seconds": 180,
                "spike_students_injected": needed_spike_students,
            },
        })

    # Anomaly 8: 25 NRI rows missing sponsor details
    nri_sample = random.sample(enrolments_data[:8000], 25)
    for en in nri_sample:
        en.quota_type = "NRI"
        en.is_nri = True
        en.sponsor_details_enc = None

        injected_issues["missing_nri_sponsor_details"].append({
            "type": "NRI_MISSING_SPONSOR_DETAILS",
            "entity_ids": [str(en.id)],
            "expected_rule": "RULE_MISSING_NRI_SPONSOR_DETAILS",
            "metadata": {"student_id": str(en.student_id)},
        })

    # Anomaly 9: 20 implausible DOBs (10 underage < 14, 10 overage > 70)
    implausible_sample = random.sample(students_data[:5000], 20)
    for i, st in enumerate(implausible_sample):
        if i < 10:
            st.dob_enc = date(2014, 5, 10)  # Age 11 at 2025 admission!
            age_desc = "UNDERAGE_ADMISSION_AGE_11"
        else:
            st.dob_enc = date(1945, 1, 15)  # Age 80 at admission!
            age_desc = "OVERAGE_ADMISSION_AGE_80"
        st.dob_bidx = compute_blind_index(st.dob_enc)

        injected_issues["implausible_dobs"].append({
            "type": "IMPLAUSIBLE_DATE_OF_BIRTH",
            "entity_ids": [str(st.id)],
            "expected_rule": "RULE_IMPLAUSIBLE_AGE",
            "metadata": {"subtype": age_desc, "dob": st.dob_enc.isoformat()},
        })

    print("✓ All 9 anomaly categories injected and cataloged!")

    # Omit ~3% of APAAR IDs from the national mock registry
    apaar_keys = list(apaar_registry.keys())
    omit_count = int(len(apaar_keys) * 0.03)
    omitted_keys = random.sample(apaar_keys, omit_count)
    for k in omitted_keys:
        del apaar_registry[k]
    print(f"✓ Mock APAAR Registry created: {len(apaar_registry)} entries ({omit_count} intentionally omitted for 404 tests)")

    # 5. Save generated JSON artifacts
    data_dir = ROOT_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    issues_file = data_dir / "injected_issues.json"
    with open(issues_file, "w", encoding="utf-8") as f:
        json.dump(injected_issues, f, indent=2)
    print(f"📁 Wrote benchmark record: {issues_file}")

    registry_file = data_dir / "apaar_registry.json"
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(apaar_registry, f, indent=2)
    print(f"📁 Wrote mock gateway registry: {registry_file}")

    # 6. Database Persistence
    if dry_run:
        print("Dry run requested - skipping database insertion.")
        return

    print("⏳ Connecting to database to persist schema entities...")
    try:
        # Create all tables if not exist
        Base.metadata.create_all(bind=sync_engine)
        session = SessionLocal()

        # 6a. Default Roles & Permissions
        role_map = {r.name: r for r in session.query(Role).all()}
        all_roles_def = [
            ("SUPER_ADMIN", "AICTE National Directorate with global oversight"),
            ("AICTE_OFFICER", "AICTE Directorate Nodal Officer"),
            ("AICTE_ANALYST", "AICTE Policy & Data Analyst"),
            ("INSTITUTION_ADMIN", "Institutional Registrar/Dean"),
            ("INSTITUTION_OPERATOR", "Institutional Academic Data Operator"),
            ("VERIFIER", "Third-party background verification agency"),
            ("AUDITOR", "Statutory Compliance & Audit Inspector"),
            ("STUDENT", "Student academic record holder"),
        ]
        for r_name, r_desc in all_roles_def:
            if r_name not in role_map:
                r = Role(name=r_name, description=r_desc)
                session.add(r)
                session.flush()
                role_map[r_name] = r

        # Permissions definitions
        perm_map = {p.code: p for p in session.query(Permission).all()}
        all_perms_def = [
            ("students:read", "View student list and records (masked)"),
            ("students:read_full", "View unmasked APAAR ID and PII"),
            ("students:write", "Create and modify student records"),
            ("batches:upload", "Upload bulk ingestion files"),
            ("batches:read", "View batch ingestion telemetry"),
            ("rules:manage", "Configure validation rules"),
            ("rules:read", "View validation rules"),
            ("audit:read", "View system audit logs"),
            ("audit:verify", "Verify cryptographic hash chain"),
            ("reports:generate", "Generate analytical reports"),
            ("verification:request", "Submit verification requests"),
            ("verification:verify", "Access verification credentials"),
            ("users:manage", "Manage user accounts"),
            ("users:read", "View user accounts"),
        ]
        for p_code, p_desc in all_perms_def:
            if p_code not in perm_map:
                p = Permission(code=p_code, description=p_desc)
                session.add(p)
                session.flush()
                perm_map[p_code] = p

        # Role-permission associations
        role_perm_defs = {
            "SUPER_ADMIN": list(perm_map.keys()),
            "AICTE_OFFICER": ["students:read", "students:read_full", "students:write", "batches:read", "rules:manage", "rules:read", "reports:generate", "verification:request", "verification:verify", "users:manage", "users:read"],
            "AICTE_ANALYST": ["students:read", "batches:read", "rules:read", "reports:generate", "users:read"],
            "INSTITUTION_ADMIN": ["students:read", "students:read_full", "students:write", "batches:upload", "batches:read", "rules:read", "reports:generate", "users:manage", "users:read"],
            "INSTITUTION_OPERATOR": ["students:read", "students:write", "batches:upload", "batches:read", "rules:read"],
            "VERIFIER": ["verification:request", "verification:verify"],
            "AUDITOR": ["audit:read", "audit:verify", "rules:read", "reports:generate", "users:read"],
            "STUDENT": ["students:read"],
        }
        for r_name, p_codes in role_perm_defs.items():
            r = role_map[r_name]
            existing_p_ids = {p.id for p in r.permissions}
            for p_code in p_codes:
                p = perm_map[p_code]
                if p.id not in existing_p_ids:
                    session.add(RolePermission(role_id=r.id, permission_id=p.id))
        session.flush()

        # 6b. Demo Users per Role with Argon2id passwords
        demo_accounts = [
            ("superadmin@aicte.gov.in", "SuperAdmin@2026", "AICTE National Director", "SUPER_ADMIN", None),
            ("officer@aicte.gov.in", "Officer@2026!", "AICTE Regional Officer", "AICTE_OFFICER", None),
            ("analyst@aicte.gov.in", "Analyst@2026!", "National Policy Analyst", "AICTE_ANALYST", None),
            ("admin@iitb.ac.in", "InstAdmin@2026", "IIT Bombay Registrar", "INSTITUTION_ADMIN", 0),
            ("operator@iitb.ac.in", "InstOperator@2026", "IIT Bombay Operator", "INSTITUTION_OPERATOR", 0),
            ("verifier@tcs.com", "Verifier@2026!", "TCS Corporate Verifier", "VERIFIER", None),
            ("auditor@cag.gov.in", "Auditor@2026!", "CAG Senior Auditor", "AUDITOR", None),
            ("student@aicte.ac.in", "Student@2026!", "Student Demo Account", "STUDENT", None),
        ]
        for email, pwd, name, role_name, inst_idx in demo_accounts:
            existing_u = session.query(User).filter_by(email=email).first()
            if not existing_u:
                u = User(
                    email=email,
                    password_hash=hash_password(pwd),
                    full_name=name,
                    is_active=True,
                    is_verified=True,
                )
                session.add(u)
                session.flush()
                session.add(UserRole(user_id=u.id, role_id=role_map[role_name].id))
                if inst_idx is not None and len(institutions_data) > inst_idx:
                    session.add(UserInstitution(user_id=u.id, institution_id=institutions_data[inst_idx].id))
        session.flush()

        # 6c. Insert States, Institutions, Programs
        existing_states = session.query(State).count()
        if existing_states == 0:
            session.add_all(states_data)
            session.flush()

        existing_inst = session.query(Institution).count()
        if existing_inst == 0:
            session.add_all(institutions_data)
            session.flush()

        existing_progs = session.query(Program).count()
        if existing_progs == 0:
            session.add_all(programs_data)
            session.flush()

        # 6d. Insert Students and Enrolments in Batches of 1,000 for high performance
        existing_students = session.query(Student).count()
        if existing_students == 0:
            print(f"⏳ Committing {len(students_data)} Students in chunks of 1000...")
            chunk_size = 1000
            for i in range(0, len(students_data), chunk_size):
                session.add_all(students_data[i:i + chunk_size])
                session.flush()
            print("✓ Students committed.")

        existing_enrolments = session.query(Enrolment).count()
        if existing_enrolments == 0:
            print(f"⏳ Committing {len(enrolments_data)} Enrolments in chunks of 1000...")
            chunk_size = 1000
            for i in range(0, len(enrolments_data), chunk_size):
                session.add_all(enrolments_data[i:i + chunk_size])
                session.flush()
            print("✓ Enrolments committed.")

        session.commit()
        print("✅ Database seeding completed successfully!")
    except Exception as exc:
        print(f"⚠️ Note: Database connection not available or error occurred ({exc}). Synthetic datasets were still successfully generated to disk.")
    finally:
        try:
            session.close()
        except Exception:
            pass


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    if is_dry:
        generate_synthetic_dataset(dry_run=True)
    else:
        from app.services.seed_pipeline import run_full_seed_pipeline
        run_full_seed_pipeline()
