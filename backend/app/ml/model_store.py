"""Model artifact storage, versioning, and lifecycle management.

Manages versioned Isolation Forest models and metadata under backend/app/ml/artifacts/:
- isolation_forest_{version}.joblib
- feature_stats_{version}.json
- metadata_{version}.json
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib

from app.ml.anomaly_detector import InstitutionRiskDetector
from app.ml.features import FEATURE_NAMES


ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


class ModelStore:
    """Manages versioned model artifacts and metadata persistence."""

    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.artifacts_dir = artifacts_dir or ARTIFACTS_DIR
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _get_active_manifest_path(self) -> Path:
        return self.artifacts_dir / "active_model.json"

    def get_active_version(self) -> str:
        """Read the currently active model version from active_model.json."""
        manifest = self._get_active_manifest_path()
        if manifest.exists():
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("active_version", "v1.0")
            except Exception:
                pass
        return "v1.0"

    def set_active_version(self, version: str) -> None:
        """Update active model version manifest."""
        manifest = self._get_active_manifest_path()
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump({
                "active_version": version,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2)

    def save_model(
        self,
        detector: InstitutionRiskDetector,
        version: str = "v1.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Save fitted detector, feature statistics, and metadata to disk."""
        if not detector.is_fitted or detector.model is None:
            raise ValueError("Cannot save an unfitted InstitutionRiskDetector.")

        model_file = self.artifacts_dir / f"isolation_forest_{version}.joblib"
        stats_file = self.artifacts_dir / f"feature_stats_{version}.json"
        meta_file = self.artifacts_dir / f"metadata_{version}.json"

        # 1. Save Isolation Forest joblib
        joblib.dump(detector.model, model_file)

        # 2. Save feature stats (Medians and MADs)
        stats_data = {
            "feature_names": FEATURE_NAMES,
            "medians": detector.feature_medians,
            "mads": detector.feature_mads,
            "n_estimators": detector.n_estimators,
            "contamination": str(detector.contamination),
            "random_state": detector.random_state,
        }
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats_data, f, indent=2)

        # 3. Save metadata
        meta_data = {
            "version": version,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "feature_count": len(FEATURE_NAMES),
            "custom_metadata": metadata or {},
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)

        # Mark as active version
        self.set_active_version(version)

        return {
            "model_path": str(model_file),
            "stats_path": str(stats_file),
            "metadata_path": str(meta_file),
            "version": version,
        }

    def load_model(self, version: Optional[str] = None) -> InstitutionRiskDetector:
        """Load a fitted detector from disk for the specified or active version."""
        ver = version or self.get_active_version()
        model_file = self.artifacts_dir / f"isolation_forest_{ver}.joblib"
        stats_file = self.artifacts_dir / f"feature_stats_{ver}.json"

        if not model_file.exists() or not stats_file.exists():
            raise FileNotFoundError(f"Model artifacts for version '{ver}' not found at {self.artifacts_dir}.")

        with open(stats_file, "r", encoding="utf-8") as f:
            stats_data = json.load(f)

        detector = InstitutionRiskDetector(
            n_estimators=stats_data.get("n_estimators", 100),
            contamination="auto",
            random_state=stats_data.get("random_state", 42),
        )
        detector.model = joblib.load(model_file)
        detector.feature_medians = stats_data.get("medians", {})
        detector.feature_mads = stats_data.get("mads", {})
        detector.is_fitted = True

        return detector

    def list_versions(self) -> List[Dict[str, Any]]:
        """List all versioned models stored in artifacts directory."""
        versions = []
        active_ver = self.get_active_version()

        for meta_file in sorted(self.artifacts_dir.glob("metadata_*.json")):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    meta["is_active"] = meta.get("version") == active_ver
                    versions.append(meta)
            except Exception:
                continue

        return versions
