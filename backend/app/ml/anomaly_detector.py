"""Anomaly detection engine for student enrollment and academic credits."""

from datetime import date
from typing import Any, Dict, List


class AnomalyDetector:
    """Detects fraud, duplicate enrollment, and academic policy violations."""

    @staticmethod
    def check_age_anomaly(dob: date, admission_year: int) -> List[Dict[str, Any]]:
        anomalies = []
        age_at_admission = admission_year - dob.year
        if age_at_admission < 16:
            anomalies.append({
                "type": "AGE_ANOMALY",
                "severity": "HIGH",
                "message": f"Student age at admission is {age_at_admission} years (under minimum threshold of 16).",
            })
        elif age_at_admission > 65:
            anomalies.append({
                "type": "AGE_ANOMALY",
                "severity": "MEDIUM",
                "message": f"Student age at admission is {age_at_admission} years.",
            })
        return anomalies

    @staticmethod
    def check_semester_credit_surge(semester: int, credits: float) -> List[Dict[str, Any]]:
        anomalies = []
        if credits > 36.0:
            anomalies.append({
                "type": "CREDIT_SURGE_ANOMALY",
                "severity": "HIGH",
                "message": f"Excessive credit allocation in semester {semester}: {credits} credits (maximum standard is 32.0).",
            })
        return anomalies
