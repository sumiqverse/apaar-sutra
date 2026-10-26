"""Peer-group comparison engine for institutional benchmarking.

Compares an institution against contextual peers of similar:
1. Institution Type (UNIVERSITY, AUTONOMOUS, AFFILIATED, STANDALONE_PGDM)
2. State / Region
3. Approved Intake Size Tier (SMALL: <500, MEDIUM: 500-1500, LARGE: >1500)

Provides peer distributions (median, mean, Q1, Q3, std) and percentile rankings
for every extracted signal.
"""

from typing import Any, Dict, List, Optional
import numpy as np


def get_size_tier(intake: int) -> str:
    """Classify an institution into an intake capacity tier."""
    if intake < 500:
        return "SMALL"
    elif intake <= 1500:
        return "MEDIUM"
    return "LARGE"


class PeerGroupComparator:
    """Builds peer groups and computes benchmark deviations."""

    def __init__(self, institutions_metadata: List[Dict[str, Any]], features_by_id: Dict[str, Dict[str, float]]):
        """
        institutions_metadata: List of dicts with keys:
            id, aicte_id, name, institution_type, state_id or state_code, approved_total_intake
        features_by_id: Dict mapping institution_id (str) -> feature dict
        """
        self.metadata = {str(item["id"]): item for item in institutions_metadata}
        self.features = {str(k): v for k, v in features_by_id.items()}

    def get_peer_group(self, target_id: str) -> Tuple_Peers:
        """Find the most specific peer group with at least 3 members."""
        target_meta = self.metadata.get(str(target_id))
        if not target_meta:
            # Fall back to all
            all_ids = list(self.features.keys())
            return all_ids, "ALL_NATIONAL"

        target_type = target_meta.get("institution_type", "AFFILIATED")
        target_state = str(target_meta.get("state_id") or target_meta.get("state_code") or "")
        intake = target_meta.get("approved_total_intake", 0)
        target_size = get_size_tier(intake)

        # Hierarchy Level 1: Type + State + Size
        peers_lvl1 = [
            inst_id for inst_id, meta in self.metadata.items()
            if inst_id in self.features
            and meta.get("institution_type") == target_type
            and str(meta.get("state_id") or meta.get("state_code") or "") == target_state
            and get_size_tier(meta.get("approved_total_intake", 0)) == target_size
        ]
        if len(peers_lvl1) >= 3:
            return peers_lvl1, f"{target_type}_{target_state}_{target_size}"

        # Hierarchy Level 2: Type + State
        peers_lvl2 = [
            inst_id for inst_id, meta in self.metadata.items()
            if inst_id in self.features
            and meta.get("institution_type") == target_type
            and str(meta.get("state_id") or meta.get("state_code") or "") == target_state
        ]
        if len(peers_lvl2) >= 3:
            return peers_lvl2, f"{target_type}_{target_state}"

        # Hierarchy Level 3: Type + Size Nationally
        peers_lvl3 = [
            inst_id for inst_id, meta in self.metadata.items()
            if inst_id in self.features
            and meta.get("institution_type") == target_type
            and get_size_tier(meta.get("approved_total_intake", 0)) == target_size
        ]
        if len(peers_lvl3) >= 3:
            return peers_lvl3, f"{target_type}_{target_size}_NATIONAL"

        # Hierarchy Level 4: Type Nationally
        peers_lvl4 = [
            inst_id for inst_id, meta in self.metadata.items()
            if inst_id in self.features
            and meta.get("institution_type") == target_type
        ]
        if len(peers_lvl4) >= 3:
            return peers_lvl4, f"{target_type}_NATIONAL"

        # Fallback Level 5: All institutions
        return list(self.features.keys()), "ALL_NATIONAL"

    def compare_institution(self, target_id: str) -> Dict[str, Any]:
        """Compute full peer benchmark report for a single institution."""
        target_id_str = str(target_id)
        target_features = self.features.get(target_id_str, {})
        peer_ids, slice_label = self.get_peer_group(target_id_str)

        peer_metrics: Dict[str, Dict[str, float]] = {}
        percentiles: Dict[str, float] = {}

        for feature_name, target_val in target_features.items():
            peer_vals = [
                self.features[pid][feature_name]
                for pid in peer_ids
                if pid in self.features and feature_name in self.features[pid]
            ]

            if not peer_vals:
                peer_vals = [target_val]

            arr = np.array(peer_vals, dtype=float)
            med = float(np.median(arr))
            mean = float(np.mean(arr))
            q1 = float(np.percentile(arr, 25))
            q3 = float(np.percentile(arr, 75))
            std = float(np.std(arr))

            # Percentile rank (percentage of peers whose value is <= target_val)
            rank = float(np.mean(arr <= target_val) * 100.0)

            # Deviation pct from peer median
            denom = abs(med) if abs(med) > 0.001 else 0.001
            dev_pct = float(((target_val - med) / denom) * 100.0)

            peer_metrics[feature_name] = {
                "median": round(med, 4),
                "mean": round(mean, 4),
                "q1": round(q1, 4),
                "q3": round(q3, 4),
                "std": round(std, 4),
                "deviation_pct": round(dev_pct, 2),
            }
            percentiles[feature_name] = round(rank, 1)

        return {
            "peer_count": len(peer_ids),
            "slice_label": slice_label,
            "peer_metrics": peer_metrics,
            "percentiles": percentiles,
        }


Tuple_Peers = tuple[List[str], str]
