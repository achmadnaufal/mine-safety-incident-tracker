"""
Near Miss Tracking and Prevention Analytics for Mining Operations.

A near miss is an unplanned event that did not result in injury, illness, or
damage but had the potential to do so. Tracking near misses is critical for
proactive safety management — every near miss is a warning before a real incident.

Author: github.com/achmadnaufal
"""
from __future__ import annotations

import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple


class NearMissTracker:
    """
    Tracks and analyzes near-miss events in mining operations.

    Near misses are categorized by work area, hazard type, and potential
    severity. This tracker computes risk ratios, trending hazards, and
    generates recommended corrective actions.

    Attributes:
        site_name (str): Name of the mining site.
        records (list): List of near-miss event records.

    Example::

        tracker = NearMissTracker(site_name="Pit-A North")
        tracker.record_event(
            date="2026-03-23",
            area="Haul Road",
            hazard_type="Near Collision",
            description="Dump truck overtook light vehicle at blind corner",
            potential_severity="Critical",
            reported_by="EMP-0421",
        )
        print(tracker.get_risk_summary())
    """

    HAZARD_TYPES = [
        "Near Collision",
        "Falling Object",
        "Slip/Trip",
        "Equipment Malfunction",
        "Electrical Hazard",
        "Ground Instability",
        "Dust/Gas Exposure",
        "Blast Proximity",
        "Unsecured Load",
        "Other",
    ]

    SEVERITY_WEIGHTS = {"Low": 1, "Medium": 2, "High": 3, "Critical": 5}
    WORK_AREAS = [
        "Pit Floor",
        "Haul Road",
        "Crusher Area",
        "Workshop",
        "Explosives Magazine",
        "Conveyor Belt",
        "Stockpile",
        "Office/Admin",
        "Other",
    ]

    def __init__(self, site_name: str = "Mine Site") -> None:
        """
        Initialize the NearMissTracker.

        Args:
            site_name: Human-readable name for the mine site (used in reports).
        """
        self.site_name = site_name
        self.records: List[Dict] = []

    # ------------------------------------------------------------------
    # Data entry
    # ------------------------------------------------------------------

    def record_event(
        self,
        date: str,
        area: str,
        hazard_type: str,
        description: str,
        potential_severity: str = "Medium",
        reported_by: Optional[str] = None,
        corrective_action: Optional[str] = None,
        shift: str = "Day",
    ) -> int:
        """
        Record a new near-miss event.

        Args:
            date: Event date in ``YYYY-MM-DD`` format.
            area: Work area where the event occurred (see ``WORK_AREAS``).
            hazard_type: Type of hazard (see ``HAZARD_TYPES``).
            description: Free-text description of what happened.
            potential_severity: Potential worst-case severity if event
                had escalated (``Low`` / ``Medium`` / ``High`` / ``Critical``).
            reported_by: Employee ID or name who reported the event.
            corrective_action: Immediate corrective action taken.
            shift: Shift during which event occurred (``Day`` / ``Night``).

        Returns:
            The integer ID assigned to this record.

        Raises:
            ValueError: If ``potential_severity`` or ``hazard_type`` is invalid.
        """
        if potential_severity not in self.SEVERITY_WEIGHTS:
            raise ValueError(
                f"Invalid severity '{potential_severity}'. "
                f"Choose from: {list(self.SEVERITY_WEIGHTS)}"
            )
        if hazard_type not in self.HAZARD_TYPES:
            raise ValueError(
                f"Invalid hazard_type '{hazard_type}'. "
                f"Choose from: {self.HAZARD_TYPES}"
            )
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise ValueError(f"date '{date}' is not in YYYY-MM-DD format.")

        record_id = len(self.records) + 1
        self.records.append(
            {
                "id": record_id,
                "date": date,
                "area": area,
                "hazard_type": hazard_type,
                "description": description,
                "potential_severity": potential_severity,
                "severity_weight": self.SEVERITY_WEIGHTS[potential_severity],
                "reported_by": reported_by,
                "corrective_action": corrective_action,
                "shift": shift,
            }
        )
        return record_id

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def get_risk_summary(self) -> Dict:
        """
        Compute high-level risk metrics across all recorded near misses.

        Returns:
            dict with keys:

            - ``total_events`` – total near-miss count
            - ``cumulative_risk_score`` – sum of severity weights
            - ``area_counts`` – near-miss count per work area
            - ``hazard_counts`` – near-miss count per hazard type
            - ``severity_distribution`` – count per severity level
            - ``top_hazard`` – hazard type with most events
            - ``top_area`` – work area with most events
            - ``night_shift_pct`` – proportion of events on night shift
        """
        if not self.records:
            return {"total_events": 0, "cumulative_risk_score": 0}

        area_counts: Counter = Counter(r["area"] for r in self.records)
        hazard_counts: Counter = Counter(r["hazard_type"] for r in self.records)
        severity_counts: Counter = Counter(
            r["potential_severity"] for r in self.records
        )
        cumulative_risk = sum(r["severity_weight"] for r in self.records)
        night_count = sum(1 for r in self.records if r["shift"] == "Night")

        return {
            "site": self.site_name,
            "total_events": len(self.records),
            "cumulative_risk_score": cumulative_risk,
            "area_counts": dict(area_counts.most_common()),
            "hazard_counts": dict(hazard_counts.most_common()),
            "severity_distribution": dict(severity_counts),
            "top_hazard": hazard_counts.most_common(1)[0][0] if hazard_counts else None,
            "top_area": area_counts.most_common(1)[0][0] if area_counts else None,
            "night_shift_pct": round(night_count / len(self.records) * 100, 1),
        }

    def get_trending_hazards(self, window_days: int = 30) -> List[Tuple[str, int]]:
        """
        Return hazard types trending in the most recent window.

        Args:
            window_days: Look-back period in days (default 30).

        Returns:
            List of ``(hazard_type, count)`` tuples sorted by count descending.
        """
        if not self.records:
            return []
        cutoff = (
            datetime.date.today() - datetime.timedelta(days=window_days)
        ).isoformat()
        recent = [r for r in self.records if r["date"] >= cutoff]
        counts: Counter = Counter(r["hazard_type"] for r in recent)
        return counts.most_common()

    def area_risk_matrix(self) -> Dict[str, Dict[str, int]]:
        """
        Build a cross-tabulation of area × severity counts.

        Returns:
            Nested dict: ``{area: {severity: count, ...}, ...}``
        """
        matrix: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {s: 0 for s in self.SEVERITY_WEIGHTS}
        )
        for record in self.records:
            matrix[record["area"]][record["potential_severity"]] += 1
        return {area: dict(severities) for area, severities in matrix.items()}

    def recommend_actions(self) -> List[str]:
        """
        Generate corrective action recommendations based on event patterns.

        Returns:
            List of recommendation strings ordered by priority.
        """
        if not self.records:
            return ["No near-miss data recorded. Begin logging events."]

        recommendations = []
        summary = self.get_risk_summary()

        top_hazard = summary.get("top_hazard")
        top_area = summary.get("top_area")

        if top_hazard == "Near Collision":
            recommendations.append(
                f"[HIGH] Implement traffic management plan at {top_area}: "
                "segregate haul trucks from light vehicles, add signage at blind spots."
            )
        if top_hazard == "Falling Object":
            recommendations.append(
                f"[HIGH] Mandatory hard hat zones and overhead netting at {top_area}."
            )
        if top_hazard == "Ground Instability":
            recommendations.append(
                "[CRITICAL] Engage geotechnical engineer for slope stability audit immediately."
            )
        if summary.get("night_shift_pct", 0) > 40:
            recommendations.append(
                "[MEDIUM] Night shift near-miss rate is elevated. "
                "Review lighting conditions and fatigue management program."
            )
        if summary["cumulative_risk_score"] > 50:
            recommendations.append(
                "[HIGH] Cumulative risk score exceeds threshold (50). "
                "Schedule emergency safety stand-down within 48 hours."
            )
        if not recommendations:
            recommendations.append(
                "[LOW] No critical patterns detected. Continue monitoring and "
                "encourage near-miss reporting culture."
            )
        return recommendations

    def export_records(self) -> List[Dict]:
        """Return all records as a list of plain dicts (suitable for JSON/CSV export)."""
        return list(self.records)

    def __len__(self) -> int:
        """Return total number of recorded near-miss events."""
        return len(self.records)

    def __repr__(self) -> str:
        return (
            f"NearMissTracker(site={self.site_name!r}, "
            f"events={len(self.records)})"
        )
