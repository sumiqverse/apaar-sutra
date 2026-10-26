"""Seed demo analytics: ML risk scores, validation issues, and alerts."""

import json
from pathlib import Path
import random
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import uuid

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from app.models.base import SessionLocal
from app.models.state import State
from app.models.institution import Institution
from app.models.program import Program
from app.models.enrolment import Enrolment
from app.models.ml import InstitutionRiskScore
from app.models.validation import ValidationIssue
from app.models.credential import Alert


def seed_analytics():
    print("🚀 Seeding rich institutional risk scores, validation issues, and alerts...")
    session = SessionLocal()
    try:
        institutions = session.query(Institution).all()
        if not institutions:
            print("No institutions found. Run generate_data.py first.")
            return

        # 1. Clear existing risk scores, validation issues, alerts
        session.query(InstitutionRiskScore).delete()
        session.query(ValidationIssue).delete()
        session.query(Alert).delete()
        session.flush()

        # Injected issues json
        injected_file = ROOT_DIR / "data" / "injected_issues.json"
        injected_data = {}
        if injected_file.exists():
            with open(injected_file, "r", encoding="utf-8") as f:
                injected_data = json.load(f)

        random.seed(42)

        # 2. Seed InstitutionRiskScore for all institutions
        for i, inst in enumerate(institutions):
            # Highlight top risk institutions
            if inst.aicte_id in ["1-100234907", "1-100234908"]:
                risk_score = random.uniform(92.0, 98.5)
                risk_level = "CRITICAL"
                factors = [
                    {
                        "feature": "enrolment_spike_yoy",
                        "deviation_sigma": 3.8,
                        "description": "Enrolment grew 240% YoY vs peer median 9%",
                    },
                    {
                        "feature": "admission_timestamp_clustering",
                        "deviation_sigma": 3.4,
                        "description": "85 admissions recorded within 180 seconds window",
                    },
                    {
                        "feature": "name_entropy_anomaly",
                        "deviation_sigma": 2.6,
                        "description": "Low surname entropy indicative of synthetic student generation",
                    },
                ]
                ghost_flags = {
                    "burst_detected": True,
                    "burst_count": 85,
                    "timestamp_window_seconds": 180,
                    "sequential_ids_detected": True,
                }
            elif inst.aicte_id in ["1-100234901", "1-100234902", "1-100234903"]:
                risk_score = random.uniform(75.0, 88.0)
                risk_level = "HIGH"
                factors = [
                    {
                        "feature": "intake_utilisation_ratio",
                        "deviation_sigma": 2.9,
                        "description": "Actual enrolment exceeds approved capacity by 40%",
                    },
                    {
                        "feature": "cross_institution_duplicates",
                        "deviation_sigma": 2.1,
                        "description": "Multiple active enrolments registered concurrently in another state",
                    },
                ]
                ghost_flags = {"burst_detected": False}
            elif i < 15:
                risk_score = random.uniform(40.0, 65.0)
                risk_level = "MEDIUM"
                factors = [
                    {
                        "feature": "apaar_validation_failure_rate",
                        "deviation_sigma": 1.7,
                        "description": "12% of student records failed Verhoeff checksum validation",
                    }
                ]
                ghost_flags = {"burst_detected": False}
            else:
                risk_score = random.uniform(5.0, 28.0)
                risk_level = "LOW"
                factors = []
                ghost_flags = {"burst_detected": False}

            prog_count = session.query(Program).filter_by(institution_id=inst.id).count()
            enr_count = session.query(Enrolment).filter_by(institution_id=inst.id).count()

            st_obj = session.query(State).filter_by(id=inst.state_id).first() if inst.state_id else None
            peer_comp = {
                "peer_group_type": inst.institution_type,
                "peer_state": st_obj.name if st_obj else "National",
                "peer_count": 14,
                "peer_median_enrolment": 360,
                "peer_median_intake": 400,
                "peer_median_utilisation_pct": 78.5,
                "peer_median_risk_score": 18.2,
                "institution_utilisation_pct": round((enr_count / max(1, inst.approved_total_intake)) * 100, 1),
            }

            metrics = {
                "total_programs": prog_count,
                "total_enrolments": enr_count,
                "approved_intake": inst.approved_total_intake,
                "warning_count": int(enr_count * 0.05),
                "error_count": int(enr_count * 0.02) if risk_level in ["HIGH", "CRITICAL"] else 0,
            }

            rs = InstitutionRiskScore(
                id=uuid.uuid4(),
                institution_id=inst.id,
                academic_year="2025-26",
                risk_score=round(risk_score, 1),
                risk_level=risk_level,
                anomaly_score=round(risk_score / 100.0, 3),
                contributing_factors=factors,
                metrics=metrics,
                peer_comparison=peer_comp,
                ghost_student_flags=ghost_flags,
                model_version="v1.0",
            )
            session.add(rs)

        # 3. Seed Validation Issues
        sample_insts = institutions[:10]
        issue_templates = [
            ("R020", "CRITICAL", "Approved intake capacity exceeded by 40% in B.Tech Computer Science & Engineering", {"overshoot_count": 24, "approved_intake": 60, "actual_enrolment": 84}),
            ("R011", "CRITICAL", "Cross-institution duplicate: student actively enrolled simultaneously in IITM Mumbai and DTU Delhi", {"apaar_id": "200000000428", "other_inst": "Delhi Technological University"}),
            ("R002", "ERROR", "Invalid APAAR ID format: Verhoeff mathematical checksum verification failed", {"field": "apaar_id", "value": "200000000199"}),
            ("R030", "WARNING", "Demographic inconsistency: Foreign National student assigned Indian reserved quota (OBC)", {"nationality": "NEPALESE", "quota": "OBC"}),
            ("R010", "ERROR", "Internal duplicate enrolment within same program and academic session", {"student_ref_id": "CSE-2025-412"}),
            ("R021", "WARNING", "Supernumerary seat allocation exceeds statutory cap of 15%", {"supernumerary_pct": 22.5, "cap_pct": 15.0}),
            ("R001", "ERROR", "Mandatory APAAR ID is missing for registered student enrolment", {"enrolment_ref": "SPIKE-CSE-0042"}),
        ]

        for idx, (rule_code, severity, msg, expl) in enumerate(issue_templates * 6):
            target_inst = sample_insts[idx % len(sample_insts)]
            prog = session.query(Program).filter_by(institution_id=target_inst.id).first()
            enr = session.query(Enrolment).filter_by(institution_id=target_inst.id).first()

            vi = ValidationIssue(
                id=uuid.uuid4(),
                rule_code=rule_code,
                severity=severity,
                institution_id=target_inst.id,
                program_id=prog.id if prog else None,
                enrolment_id=enr.id if enr else None,
                message=msg,
                explanation=expl,
                status="OPEN",
            )
            session.add(vi)

        # 4. Seed Live Alerts
        alert_templates = [
            ("INTAKE_CAP_EXCEEDED", "CRITICAL", "Critical Intake Breach: 6 Institutions reported enrolment exceeding approved AICTE caps"),
            ("BURST_ADMISSION_ANOMALY", "CRITICAL", "Burst Admission Alert: 85 students admitted in 180 seconds at Pune Institute of Technology & Science"),
            ("CROSS_INSTITUTION_DUPLICATE", "CRITICAL", "Pan-India Conflict: 40 active dual-enrolments flagged across state borders"),
            ("CHECKSUM_FAILURE_SPIKE", "ERROR", "Data Quality Alert: High concentration of invalid APAAR IDs in B.Tech batch"),
            ("RESERVATION_INCONSISTENCY", "WARNING", "Demographic Mismatch: Foreign nationals enrolled against reserved domestic seats"),
            ("SUPERNUMERARY_CAP_BREACH", "WARNING", "Policy Deviation: NRI/Supernumerary quota exceeds 15% statutory threshold"),
        ]

        for i, (atype, sev, amsg) in enumerate(alert_templates * 3):
            target_inst = institutions[i % len(institutions)]
            alt = Alert(
                id=uuid.uuid4(),
                type=atype,
                severity=sev,
                institution_id=target_inst.id,
                message=amsg,
                status="NEW" if i < 6 else ("ASSIGNED" if i < 12 else "RESOLVED"),
            )
            session.add(alt)

        session.commit()
        print(f"✓ Seeded {len(institutions)} Risk Scores, 42 Validation Issues, and 18 Live Alerts!")
    except Exception as e:
        session.rollback()
        print(f"Error seeding analytics: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_analytics()
