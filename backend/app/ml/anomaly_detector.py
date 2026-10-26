"""Institutional anomaly detection engine combining Isolation Forest and Robust Z-Scores.

Provides:
1. Robust Z-Score baseline using Median and Median Absolute Deviation (MAD).
2. Isolation Forest model training and scoring.
3. Calibrated 0-100 risk score with categorical severity (LOW, MEDIUM, HIGH, CRITICAL).
4. Plain-English explainability describing the top contributing factors relative to peer medians.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest

from app.ml.features import FEATURE_NAMES
from app.ml.peer_comparison import PeerGroupComparator


def compute_plain_english_factor(
    feature_name: str,
    inst_val: float,
    peer_med: float,
    dev_pct: float,
) -> str:
    """Generate a clean, plain-English explanation for a deviating feature."""
    if feature_name == "yoy_enrolment_growth":
        growth_pct = round(inst_val * 100.0, 1)
        med_pct = round(peer_med * 100.0, 1)
        direction = "grew" if growth_pct >= 0 else "contracted"
        return f"Enrolment {direction} {abs(growth_pct)}% YoY vs peer median {med_pct}%"

    elif feature_name == "admission_burst_index":
        burst_pct = round(inst_val * 100.0, 1)
        med_pct = round(peer_med * 100.0, 1)
        return f"Admission date clustering is {burst_pct}% vs peer median {med_pct}% (burst admission anomaly)"

    elif feature_name == "apaar_failure_share":
        val_pct = round(inst_val * 100.0, 1)
        med_pct = round(peer_med * 100.0, 1)
        return f"Share of APAAR verification failures is {val_pct}% vs peer median {med_pct}%"

    elif feature_name == "enrolment_to_intake_ratio":
        return f"Enrolment-to-intake ratio is {inst_val:.2f}x vs peer median {peer_med:.2f}x"

    elif feature_name == "exact_intake_match_freq":
        val_pct = round(inst_val * 100.0, 1)
        med_pct = round(peer_med * 100.0, 1)
        return f"Exact intake match frequency is {val_pct}% across programs vs peer median {med_pct}%"

    elif feature_name == "surname_entropy":
        return f"Surname entropy is {inst_val:.2f} bits vs peer median {peer_med:.2f} bits (low demographic variance)"

    elif feature_name == "dob_repeat_ratio":
        val_pct = round(inst_val * 100.0, 1)
        med_pct = round(peer_med * 100.0, 1)
        return f"DOB repeat ratio is {val_pct}% vs peer median {med_pct}% (synthetic cluster signal)"

    elif feature_name == "warning_record_share":
        val_pct = round(inst_val * 100.0, 1)
        med_pct = round(peer_med * 100.0, 1)
        return f"Share of records with validation warnings is {val_pct}% vs peer median {med_pct}%"

    elif feature_name == "supernumerary_quota_share":
        val_pct = round(inst_val * 100.0, 1)
        med_pct = round(peer_med * 100.0, 1)
        return f"Supernumerary and NRI quota share is {val_pct}% vs peer median {med_pct}%"

    return f"{feature_name} is {inst_val:.2f} vs peer median {peer_med:.2f} (deviation {dev_pct:+.1f}%)"


class InstitutionRiskDetector:
    """Trains Isolation Forest and produces explainable 0-100 risk assessments."""

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float | str = "auto",
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.model: Optional[IsolationForest] = None
        self.feature_medians: Dict[str, float] = {}
        self.feature_mads: Dict[str, float] = {}
        self.is_fitted: bool = False

    def fit(self, features_by_id: Dict[str, Dict[str, float]]) -> "InstitutionRiskDetector":
        """Fit Isolation Forest and compute Robust Z-Score baselines across institutional cohort."""
        if not features_by_id:
            raise ValueError("Cannot fit model on empty feature dataset.")

        ids = list(features_by_id.keys())
        X = np.array([
            [features_by_id[inst_id].get(feat, 0.0) for feat in FEATURE_NAMES]
            for inst_id in ids
        ], dtype=float)

        # 1. Compute Median and MAD for Robust Z-Score baseline
        for i, feat in enumerate(FEATURE_NAMES):
            col = X[:, i]
            med = float(np.median(col))
            mad = float(np.median(np.abs(col - med)))
            if mad < 1e-6:
                mad = float(np.std(col)) if np.std(col) > 1e-6 else 1.0
            self.feature_medians[feat] = med
            self.feature_mads[feat] = mad

        # 2. Fit Isolation Forest
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self.model.fit(X)
        self.is_fitted = True
        return self

    def compute_robust_z_scores(self, feature_dict: Dict[str, float]) -> Dict[str, float]:
        """Compute feature-wise robust Z-scores using stored cohort Medians and MADs."""
        z_scores: Dict[str, float] = {}
        for feat in FEATURE_NAMES:
            val = feature_dict.get(feat, 0.0)
            med = self.feature_medians.get(feat, 0.0)
            mad = self.feature_mads.get(feat, 1.0)
            # For entropy, lower entropy is more anomalous!
            if feat == "surname_entropy":
                z = (med - val) / (1.4826 * mad) if val < med else 0.0
            else:
                z = (val - med) / (1.4826 * mad)
            z_scores[feat] = round(float(z), 4)
        return z_scores

    def score_institution(
        self,
        institution_id: str,
        feature_dict: Dict[str, float],
        peer_comparator: Optional[PeerGroupComparator] = None,
    ) -> Dict[str, Any]:
        """Compute calibrated risk score (0-100), severity, and top explainability factors."""
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model must be fitted before scoring institutions.")

        # Vectorize features
        x_vec = np.array([[feature_dict.get(feat, 0.0) for feat in FEATURE_NAMES]], dtype=float)

        # 1. Isolation Forest score
        decision_score = float(self.model.decision_function(x_vec)[0])
        # Mapping decision function to 0-100: negative decision scores indicate higher anomaly
        if_component = float(np.clip(50.0 - (decision_score * 180.0), 0.0, 100.0))

        # 2. Robust Z-Score baseline component
        z_scores = self.compute_robust_z_scores(feature_dict)
        positive_z = [max(0.0, z) for z in z_scores.values()]
        max_z = max(positive_z) if positive_z else 0.0
        # If an institution has a severe spike (Z > 5.0), the robust score reflects it directly
        z_component = float(np.clip(max_z * 12.5, 0.0, 100.0))

        # 3. Combined calibrated risk score
        combined_score = (0.50 * if_component) + (0.50 * z_component)
        risk_score = round(float(np.clip(combined_score, 0.0, 100.0)), 1)

        # Severity categorization
        if risk_score >= 80.0:
            risk_level = "CRITICAL"
        elif risk_score >= 60.0:
            risk_level = "HIGH"
        elif risk_score >= 35.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # 4. Peer group comparison & Explainability
        if peer_comparator:
            peer_report = peer_comparator.compare_institution(institution_id)
            peer_metrics = peer_report.get("peer_metrics", {})
        else:
            peer_report = {}
            peer_metrics = {}

        contributing_factors: List[Dict[str, Any]] = []
        # Sort features by anomaly severity (using z-score and peer deviation)
        factor_candidates = []
        for feat in FEATURE_NAMES:
            inst_val = feature_dict.get(feat, 0.0)
            z_val = z_scores.get(feat, 0.0)

            peer_info = peer_metrics.get(feat, {})
            peer_med = peer_info.get("median", self.feature_medians.get(feat, 0.0))
            dev_pct = peer_info.get("deviation_pct", 0.0)

            # Saliency score: combination of Z-score and deviation percentage
            saliency = abs(z_val) + (abs(dev_pct) / 100.0)

            factor_candidates.append({
                "feature": feat,
                "institution_value": inst_val,
                "peer_median": peer_med,
                "deviation_pct": dev_pct,
                "z_score": z_val,
                "saliency": saliency,
            })

        # Select top 3 contributing factors
        factor_candidates.sort(key=lambda x: x["saliency"], reverse=True)
        for item in factor_candidates[:3]:
            plain_text = compute_plain_english_factor(
                feature_name=item["feature"],
                inst_val=item["institution_value"],
                peer_med=item["peer_median"],
                dev_pct=item["deviation_pct"],
            )
            contributing_factors.append({
                "feature": item["feature"],
                "institution_value": round(item["institution_value"], 4),
                "peer_median": round(item["peer_median"], 4),
                "deviation_pct": round(item["deviation_pct"], 2),
                "z_score": round(item["z_score"], 2),
                "plain_english": plain_text,
            })

        return {
            "institution_id": institution_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "anomaly_score": round(decision_score, 4),
            "if_component": round(if_component, 2),
            "z_component": round(z_component, 2),
            "metrics": feature_dict,
            "robust_z_scores": z_scores,
            "contributing_factors": contributing_factors,
            "peer_comparison": peer_report,
        }

    def score_all(
        self,
        features_by_id: Dict[str, Dict[str, float]],
        peer_comparator: Optional[PeerGroupComparator] = None,
    ) -> List[Dict[str, Any]]:
        """Score all institutions and return list sorted by risk_score descending."""
        scored = [
            self.score_institution(inst_id, feat_dict, peer_comparator)
            for inst_id, feat_dict in features_by_id.items()
        ]
        scored.sort(key=lambda x: x["risk_score"], reverse=True)
        return scored
