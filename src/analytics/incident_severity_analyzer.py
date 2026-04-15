"""Analyse and classify safety incident severity in mining operations.

Provides :class:`SeverityAnalyzer` for recording individual incident events,
computing severity distributions, and aggregating injury counts.  Severity
levels follow the ICMM Safety Performance Framework:

- **Low** (weight 1) — minor first-aid incident, no lost time.
- **Medium** (weight 2) — medical treatment required, restricted duty.
- **High** (weight 3) — lost-time injury or hospitalisation.
- **Critical** (weight 5) — fatality or permanent disability potential.

Example::

    from src.analytics.incident_severity_analyzer import SeverityAnalyzer

    analyzer = SeverityAnalyzer()
    analyzer.add_incident("2026-01-15", "High", "Conveyor belt entanglement", injured=1)
    analyzer.add_incident("2026-02-03", "Medium", "Slip on haul road", injured=0)

    print(analyzer.get_severity_distribution())
    print(analyzer.get_total_injured())
    print(analyzer.calculate_weighted_risk_score())
"""

from __future__ import annotations

import copy
import datetime
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Mapping of severity label → numeric weight used for risk scoring.
SEVERITY_WEIGHTS: Dict[str, int] = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 5,
}


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class SeverityAnalyzer:
    """Analyse incident severity patterns in open-cut mining operations.

    Records are stored as immutable dicts.  All mutation methods (e.g.
    :meth:`add_incident`) append a *new* dict to the internal list rather than
    modifying existing entries.

    Attributes:
        incidents (list[dict]): Read-only list of recorded incident dicts.
            Each dict has keys: ``date``, ``incident_id``, ``severity``,
            ``description``, ``injured``, ``location``.

    Example::

        analyzer = SeverityAnalyzer()
        analyzer.add_incident(
            date="2026-03-10",
            severity="Critical",
            description="Highwall collapse at Pit-B bench 7",
            injured=2,
            location="Pit-B Bench 7",
        )
        dist = analyzer.get_severity_distribution()
        # → {"Low": 0, "Medium": 0, "High": 0, "Critical": 1}
    """

    #: Valid severity labels.
    SEVERITY_LEVELS: Dict[str, int] = SEVERITY_WEIGHTS

    def __init__(self) -> None:
        """Initialise the analyzer with an empty incident list."""
        self._incidents: List[Dict] = []

    @property
    def incidents(self) -> List[Dict]:
        """Read-only view of recorded incidents.

        Returns:
            A deep copy of the internal incident list so callers cannot mutate
            state by modifying the returned dicts.
        """
        return copy.deepcopy(self._incidents)

    # ------------------------------------------------------------------
    # Data entry
    # ------------------------------------------------------------------

    def add_incident(
        self,
        date: str,
        severity: str,
        description: str,
        injured: int = 0,
        location: str = "",
        incident_id: str = "",
    ) -> int:
        """Record a new safety incident.

        Args:
            date: Incident date in ``YYYY-MM-DD`` format.
            severity: Severity classification — must be one of
                ``Low``, ``Medium``, ``High``, or ``Critical``.
            description: Free-text description of the incident.
            injured: Number of persons injured (must be >= 0, default 0).
            location: Work area or location description (optional).
            incident_id: Unique identifier string (optional; auto-generated
                as sequential integer string if omitted).

        Returns:
            Integer index (1-based) of the newly recorded incident.

        Raises:
            ValueError: If ``severity`` is not a valid level.
            ValueError: If ``injured`` is negative.
            ValueError: If ``date`` is not in ``YYYY-MM-DD`` format.
            ValueError: If ``incident_id`` is provided and already exists.
        """
        if severity not in self.SEVERITY_LEVELS:
            raise ValueError(
                f"Invalid severity '{severity}'. "
                f"Valid values: {sorted(self.SEVERITY_LEVELS)}"
            )
        if injured < 0:
            raise ValueError(
                f"Injured count cannot be negative; got {injured}."
            )
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise ValueError(
                f"date '{date}' is not in YYYY-MM-DD format."
            )

        auto_id = incident_id or str(len(self._incidents) + 1)
        existing_ids = {inc["incident_id"] for inc in self._incidents}
        if auto_id in existing_ids:
            raise ValueError(
                f"incident_id '{auto_id}' already exists. "
                "Each incident must have a unique ID."
            )

        record: Dict = {
            "incident_id": auto_id,
            "date": date,
            "severity": severity,
            "description": description,
            "injured": injured,
            "location": location.strip(),
            "severity_weight": self.SEVERITY_LEVELS[severity],
        }
        self._incidents = self._incidents + [record]
        return len(self._incidents)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def get_severity_distribution(self) -> Dict[str, int]:
        """Return a count of incidents per severity level.

        All severity levels are included, even those with zero incidents.

        Returns:
            Dict mapping severity label → incident count.

        Example::

            {"Low": 2, "Medium": 5, "High": 3, "Critical": 1}
        """
        dist: Dict[str, int] = {level: 0 for level in self.SEVERITY_LEVELS}
        for incident in self._incidents:
            dist[incident["severity"]] += 1
        return dist

    def get_total_injured(self) -> int:
        """Return the total number of persons injured across all incidents.

        Returns:
            Sum of the ``injured`` field over all recorded incidents.
        """
        return sum(inc["injured"] for inc in self._incidents)

    def calculate_weighted_risk_score(self) -> int:
        """Compute the cumulative severity-weighted risk score.

        Each incident contributes its ``severity_weight`` to the total.
        Higher totals indicate a more hazardous incident portfolio.

        Returns:
            Integer cumulative risk score.
        """
        return sum(inc["severity_weight"] for inc in self._incidents)

    def get_incidents_by_severity(self, severity: str) -> List[Dict]:
        """Return all incidents matching a specific severity level.

        Args:
            severity: Target severity label (``Low``, ``Medium``, ``High``,
                or ``Critical``).

        Returns:
            List of matching incident dicts.  Returns an empty list when
            ``severity`` is invalid or no incidents match.
        """
        if severity not in self.SEVERITY_LEVELS:
            return []
        return [inc for inc in self._incidents if inc["severity"] == severity]

    def get_top_locations(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """Return the locations with the most recorded incidents.

        Args:
            top_n: Maximum number of locations to return (default 5).

        Returns:
            List of ``(location, count)`` tuples sorted by count descending.
            Incidents with a blank location are grouped under ``"(unknown)"``.
        """
        from collections import Counter

        locations = [
            inc["location"] if inc["location"] else "(unknown)"
            for inc in self._incidents
        ]
        counter: Counter = Counter(locations)
        return counter.most_common(top_n)

    def summary(self) -> Dict[str, object]:
        """Return a high-level summary of all recorded incidents.

        Returns:
            Dict with keys:

            - ``total_incidents``
            - ``total_injured``
            - ``weighted_risk_score``
            - ``severity_distribution``
            - ``top_locations``
        """
        return {
            "total_incidents": len(self._incidents),
            "total_injured": self.get_total_injured(),
            "weighted_risk_score": self.calculate_weighted_risk_score(),
            "severity_distribution": self.get_severity_distribution(),
            "top_locations": self.get_top_locations(),
        }
