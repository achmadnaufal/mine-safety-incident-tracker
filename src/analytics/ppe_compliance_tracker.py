"""
PPE Compliance Tracker
========================
Track, score, and report personal protective equipment (PPE) compliance
for open-cut and underground coal mining operations.

Follows Indonesian mining safety regulations (Kepmen ESDM 1827K/30/MEM/2018)
and ICMM (2019) Health and Safety Critical Controls Framework.

PPE Categories
--------------
- head     : hard hat (mandatory in all zones)
- eye      : safety glasses / face shield
- hearing  : earplugs / earmuffs (mandatory in high-noise zones)
- foot     : safety boots (mandatory in all zones)
- body     : hi-vis vest (mandatory near mobile plant)
- hand     : safety gloves (task-dependent)
- respiratory: dust mask / PAPR (mandatory in dusty / enclosed zones)

References
----------
- ICMM (2019) Health and Safety: Critical Control Management Guide.
- Kepmen ESDM 1827K/30/MEM/2018 on Mine Safety Technical Guidelines.
- ILO (2022) Safety and Health in Mining Guidelines, 2nd ed. Geneva.

Example
-------
>>> from src.analytics.ppe_compliance_tracker import PPEComplianceTracker, InspectionRecord
>>> tracker = PPEComplianceTracker(site_id="SITE-01", zone="open_cut")
>>> tracker.log_inspection(InspectionRecord(
...     worker_id="W-001", date="2026-03-30", ppe_worn=["head","foot","eye","hearing"],
...     zone="open_cut", inspector_id="INS-07",
... ))
>>> report = tracker.daily_report("2026-03-30")
>>> print(f"Compliance rate: {report['compliance_rate_pct']:.1f}%")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

PPEItem = str   # "head", "eye", "hearing", "foot", "body", "hand", "respiratory"
Zone = str      # "open_cut", "underground", "wash_plant", "workshop", "control_room"

# Required PPE per zone (ICMM + Kepmen ESDM 1827K)
_ZONE_REQUIREMENTS: Dict[str, List[str]] = {
    "open_cut":      ["head", "foot", "eye", "hearing", "body"],
    "underground":   ["head", "foot", "eye", "hearing", "body", "respiratory"],
    "wash_plant":    ["head", "foot", "eye", "hearing", "body", "hand"],
    "workshop":      ["head", "foot", "eye", "hand"],
    "control_room":  ["head", "foot"],
}

VALID_ZONES = frozenset(_ZONE_REQUIREMENTS.keys())
ALL_PPE_ITEMS = frozenset(["head", "eye", "hearing", "foot", "body", "hand", "respiratory"])

# PPE item severity weights for partial compliance scoring
_PPE_WEIGHT: Dict[str, float] = {
    "head": 2.0,         # fatality risk from falling objects
    "foot": 1.5,
    "eye": 1.5,
    "hearing": 1.0,
    "body": 1.0,
    "hand": 0.8,
    "respiratory": 1.8,  # silicosis / black lung risk
}


@dataclass
class InspectionRecord:
    """A single PPE compliance inspection for one worker."""
    worker_id: str
    date: str            # YYYY-MM-DD
    ppe_worn: List[str]  # list of PPE items observed
    zone: Zone
    inspector_id: str = ""
    shift: str = "day"   # "day" or "night"
    notes: str = ""

    def __post_init__(self):
        if not self.worker_id:
            raise ValueError("worker_id must not be empty")
        if not self.date:
            raise ValueError("date must not be empty")
        if self.zone not in VALID_ZONES:
            raise ValueError(f"zone must be one of {sorted(VALID_ZONES)}")
        for item in self.ppe_worn:
            if item not in ALL_PPE_ITEMS:
                raise ValueError(f"Unknown PPE item: '{item}'. Valid: {sorted(ALL_PPE_ITEMS)}")
        if self.shift not in ("day", "night"):
            raise ValueError("shift must be 'day' or 'night'")


@dataclass
class ComplianceScore:
    """Compliance result for a single inspection."""
    worker_id: str
    date: str
    zone: str
    required_ppe: List[str]
    worn_ppe: List[str]
    missing_ppe: List[str]
    extra_ppe: List[str]          # PPE worn beyond requirement
    full_compliance: bool
    weighted_score: float         # 0–100, severity-weighted
    risk_level: str               # OK / LOW / MODERATE / HIGH / CRITICAL

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "date": self.date,
            "zone": self.zone,
            "required_ppe": self.required_ppe,
            "worn_ppe": self.worn_ppe,
            "missing_ppe": self.missing_ppe,
            "full_compliance": self.full_compliance,
            "weighted_score": round(self.weighted_score, 2),
            "risk_level": self.risk_level,
        }


class PPEComplianceTracker:
    """
    Track PPE compliance across workers, zones, and dates.

    Parameters
    ----------
    site_id : str
        Mine site identifier.
    zone : Zone
        Default zone for inspections (can be overridden per record).
    minimum_compliance_threshold_pct : float
        Site compliance target (default 95%). Used for alert generation.
    """

    def __init__(
        self,
        site_id: str,
        zone: Zone = "open_cut",
        minimum_compliance_threshold_pct: float = 95.0,
    ) -> None:
        if not site_id:
            raise ValueError("site_id must not be empty")
        if zone not in VALID_ZONES:
            raise ValueError(f"zone must be one of {sorted(VALID_ZONES)}")
        if not (0.0 < minimum_compliance_threshold_pct <= 100.0):
            raise ValueError("minimum_compliance_threshold_pct must be in (0, 100]")

        self.site_id = site_id
        self.zone = zone
        self.threshold = minimum_compliance_threshold_pct
        self._records: List[InspectionRecord] = []

    # ------------------------------------------------------------------
    # Record management
    # ------------------------------------------------------------------

    def log_inspection(self, record: InspectionRecord) -> ComplianceScore:
        """
        Log a PPE inspection and return its compliance score.

        Parameters
        ----------
        record : InspectionRecord

        Returns
        -------
        ComplianceScore
        """
        self._records.append(record)
        return self._score_record(record)

    def log_batch(self, records: List[InspectionRecord]) -> List[ComplianceScore]:
        """Log multiple inspection records at once."""
        return [self.log_inspection(r) for r in records]

    def clear(self) -> None:
        """Remove all logged records."""
        self._records.clear()

    @property
    def total_inspections(self) -> int:
        return len(self._records)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def daily_report(self, date: str) -> dict:
        """
        Summarise compliance for a given date (YYYY-MM-DD).

        Returns
        -------
        dict with compliance_rate_pct, full_compliance_count, violations, alerts
        """
        day_records = [r for r in self._records if r.date == date]
        if not day_records:
            return {"date": date, "inspections": 0, "compliance_rate_pct": None, "message": "No inspections found."}

        scores = [self._score_record(r) for r in day_records]
        fully_compliant = sum(1 for s in scores if s.full_compliance)
        compliance_pct = fully_compliant / len(scores) * 100.0
        violators = [s for s in scores if not s.full_compliance]
        most_missed = self._most_missed_items(scores)

        alerts = []
        if compliance_pct < self.threshold:
            alerts.append(f"ALERT: Site compliance {compliance_pct:.1f}% below target {self.threshold:.1f}%")
        critical_violations = [s for s in violators if s.risk_level in ("HIGH", "CRITICAL")]
        if critical_violations:
            alerts.append(f"CRITICAL: {len(critical_violations)} worker(s) missing high-risk PPE")

        return {
            "date": date,
            "site_id": self.site_id,
            "inspections": len(scores),
            "fully_compliant": fully_compliant,
            "violations": len(violators),
            "compliance_rate_pct": round(compliance_pct, 2),
            "most_missed_ppe": most_missed,
            "alerts": alerts,
            "violator_ids": [s.worker_id for s in violators],
        }

    def worker_history(self, worker_id: str) -> dict:
        """
        Return compliance history for a specific worker.

        Returns
        -------
        dict with n_inspections, full_compliance_rate_pct, last_violation_date, recurring_missing_ppe
        """
        records = [r for r in self._records if r.worker_id == worker_id]
        if not records:
            return {"worker_id": worker_id, "n_inspections": 0, "message": "No records found."}

        scores = [self._score_record(r) for r in records]
        fc_rate = sum(1 for s in scores if s.full_compliance) / len(scores) * 100.0
        violations = [s for s in scores if not s.full_compliance]
        last_viol = max((s.date for s in violations), default=None)
        all_missing: List[str] = []
        for v in violations:
            all_missing.extend(v.missing_ppe)
        from collections import Counter
        recurring = [item for item, cnt in Counter(all_missing).most_common() if cnt >= 2]

        return {
            "worker_id": worker_id,
            "n_inspections": len(scores),
            "full_compliance_rate_pct": round(fc_rate, 2),
            "violations_count": len(violations),
            "last_violation_date": last_viol,
            "recurring_missing_ppe": recurring,
        }

    def zone_summary(self) -> List[dict]:
        """
        Compliance summary grouped by zone.

        Returns
        -------
        list of dicts sorted by compliance_rate_pct ascending (worst first)
        """
        from collections import defaultdict
        zone_scores: Dict[str, List[ComplianceScore]] = defaultdict(list)
        for r in self._records:
            zone_scores[r.zone].append(self._score_record(r))

        result = []
        for z, scores in zone_scores.items():
            fc = sum(1 for s in scores if s.full_compliance)
            result.append({
                "zone": z,
                "total_inspections": len(scores),
                "fully_compliant": fc,
                "compliance_rate_pct": round(fc / len(scores) * 100, 2) if scores else 0.0,
                "mean_weighted_score": round(sum(s.weighted_score for s in scores) / len(scores), 2),
                "below_target": (fc / len(scores) * 100 < self.threshold) if scores else True,
            })
        return sorted(result, key=lambda x: x["compliance_rate_pct"])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _score_record(self, record: InspectionRecord) -> ComplianceScore:
        required = _ZONE_REQUIREMENTS.get(record.zone, [])
        worn = set(record.ppe_worn)
        req_set = set(required)
        missing = sorted(req_set - worn)
        extra = sorted(worn - req_set)
        full = len(missing) == 0

        # Weighted score: penalise missing items by their severity weight
        if not required:
            w_score = 100.0
        else:
            total_weight = sum(_PPE_WEIGHT.get(p, 1.0) for p in required)
            missing_weight = sum(_PPE_WEIGHT.get(p, 1.0) for p in missing)
            w_score = max(0.0, (total_weight - missing_weight) / total_weight * 100.0)

        # Risk level based on missing items
        risk = self._risk_level(missing)

        return ComplianceScore(
            worker_id=record.worker_id,
            date=record.date,
            zone=record.zone,
            required_ppe=required,
            worn_ppe=list(worn),
            missing_ppe=missing,
            extra_ppe=extra,
            full_compliance=full,
            weighted_score=round(w_score, 4),
            risk_level=risk,
        )

    @staticmethod
    def _risk_level(missing: List[str]) -> str:
        if not missing:
            return "OK"
        # Critical items missing
        if "head" in missing or "respiratory" in missing:
            return "CRITICAL"
        if "foot" in missing or "eye" in missing:
            return "HIGH"
        if len(missing) >= 2:
            return "MODERATE"
        return "LOW"

    @staticmethod
    def _most_missed_items(scores: List[ComplianceScore]) -> List[Tuple[str, int]]:
        from collections import Counter
        missed: List[str] = []
        for s in scores:
            missed.extend(s.missing_ppe)
        return Counter(missed).most_common(5)
