"""Database seeding script for APAAR-Sutra."""

import hashlib
import uuid
from datetime import date
from sqlalchemy.orm import Session

from app.models.base import SessionLocal, sync_engine, Base
from app.models.institution import Institution
from app.models.student import Student, AcademicRecord
from app.models.audit_log import AuditLog
from app.validation.apaar_rules import generate_verhoeff_check_digit


def hash_ref(val: str) -> str:
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def seed_database() -> None:
    print("🚀 Initializing database schema...")
    Base.metadata.create_all(bind=sync_engine)

    session: Session = SessionLocal()
    try:
        # 1. Seed Institutions
        inst1_aicte_id = "1-100234901"
        inst1 = session.query(Institution).filter_by(aicte_id=inst1_aicte_id).first()
        if not inst1:
            inst1 = Institution(
                id=uuid.uuid4(),
                aicte_id=inst1_aicte_id,
                name="Indian Institute of Technology & Management (IITM)",
                state="Maharashtra",
                district="Mumbai Suburban",
                is_active=True,
                contact_email="registrar@iitm.ac.in",
            )
            session.add(inst1)
            session.flush()
            print(f"✓ Created Institution: {inst1.name}")

        inst2_aicte_id = "1-200987112"
        inst2 = session.query(Institution).filter_by(aicte_id=inst2_aicte_id).first()
        if not inst2:
            inst2 = Institution(
                id=uuid.uuid4(),
                aicte_id=inst2_aicte_id,
                name="Delhi Technological University (DTU)",
                state="Delhi",
                district="North Delhi",
                is_active=True,
                contact_email="records@dtu.ac.in",
            )
            session.add(inst2)
            session.flush()
            print(f"✓ Created Institution: {inst2.name}")

        # 2. Seed Student 1 with mathematical Verhoeff check digit
        prefix1 = "98765432101"
        apaar1 = prefix1 + generate_verhoeff_check_digit(prefix1)
        student1 = session.query(Student).filter_by(apaar_id=apaar1).first()
        if not student1:
            student1 = Student(
                id=uuid.uuid4(),
                apaar_id=apaar1,
                institution_id=inst1.id,
                first_name="Aarav",
                last_name="Sharma",
                dob=date(2003, 5, 15),
                gender="MALE",
                aadhaar_hash=hash_ref("999988887777"),
                enrollment_number="EN2021001",
                program_name="B.Tech Computer Science & Engineering",
                admission_year=2021,
                status="ACTIVE",
                verification_status="VERIFIED",
            )
            session.add(student1)
            session.flush()

            # Add Academic Records
            records = [
                AcademicRecord(
                    id=uuid.uuid4(),
                    student_id=student1.id,
                    semester=1,
                    course_code="CS101",
                    course_name="Data Structures & Algorithms",
                    credits=4.0,
                    grade_point=9.5,
                    result_status="PASS",
                ),
                AcademicRecord(
                    id=uuid.uuid4(),
                    student_id=student1.id,
                    semester=2,
                    course_code="CS102",
                    course_name="Computer Architecture",
                    credits=4.0,
                    grade_point=9.0,
                    result_status="PASS",
                ),
                AcademicRecord(
                    id=uuid.uuid4(),
                    student_id=student1.id,
                    semester=3,
                    course_code="CS201",
                    course_name="Database Management Systems",
                    credits=4.0,
                    grade_point=9.2,
                    result_status="PASS",
                ),
            ]
            session.add_all(records)
            print(f"✓ Created Student {student1.first_name} {student1.last_name} with APAAR ID: {apaar1}")

        # Commit initial seed
        session.commit()
        print("✅ Database seeding completed successfully!")
    except Exception as exc:
        session.rollback()
        print(f"❌ Seeding error: {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
