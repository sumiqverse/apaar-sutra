"""ML, anomaly detection, and fraud intelligence layer for APAAR-Sutra."""

from app.ml.features import FEATURE_NAMES, InstitutionFeatureExtractor
from app.ml.peer_comparison import PeerGroupComparator
from app.ml.anomaly_detector import InstitutionRiskDetector, compute_plain_english_factor
from app.ml.fuzzy_dedup import IndianNameNormalizer, CandidateBlocker, FuzzyDeduplicator
from app.ml.ghost_students import GhostStudentDetector
from app.ml.model_store import ModelStore

__all__ = [
    "FEATURE_NAMES",
    "InstitutionFeatureExtractor",
    "PeerGroupComparator",
    "InstitutionRiskDetector",
    "compute_plain_english_factor",
    "IndianNameNormalizer",
    "CandidateBlocker",
    "FuzzyDeduplicator",
    "GhostStudentDetector",
    "ModelStore",
]
