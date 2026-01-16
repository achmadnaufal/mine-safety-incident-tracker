"""
Emergency response performance evaluator for mining operations.

Measures the effectiveness of emergency response drills and actual incident
responses using ICMM Principles and MSHA emergency response timing benchmarks.
Evaluates response time, mustering efficiency, communication cascade speed,
and post-event corrective action closure rates.

Key metrics:
- Response Time Index (RTI): actual vs target response time
- Muster Completeness Score (MCS): % personnel accounted for within window
- Communication Cascade Rate (CCR): time to notify all key stakeholders
- Action Closure Rate (ACR): % corrective actions closed within due date

References:
    - ICMM (2021) Emergency Preparedness and Response — Good Practice Guide
    - MSHA (2022) Emergency Response Plan requirements (30 CFR Part 49)
    - ISO 45001:2018 Occupational Health and Safety Management
    - JORC (2012) Emergency response protocols for underground operations
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class EmergencyType(Enum):
    """Classification of mining emergency event types."""
    FIRE = "fire"
    EXPLOSION = "explosion"
    COLLAPSE = "collapse"
    GAS_RELEASE = "gas_release"
    FLOOD = "flood"
    MACHINERY_ACCIDENT = "machinery_accident"
    MEDICAL = "medical"
    ENVIRONMENTAL_SPILL = "environmental_spill"
    DRILL = "drill"                  # Planned exercise


class ResponseGrade(Enum):
    """Overall emergency response performance grade."""
    EXCELLENT = "excellent"     # RTI ≥ 0.90 + MCS ≥ 95%
    SATISFACTORY = "satisfactory"
    NEEDS_IMPROVEMENT = "needs_improvement"
    UNSATISFACTORY = "unsatisfactory"


@dataclass
class EmergencyEvent:
    """
    Record of an emergency response event (drill or actual incident).

    Attributes:
        event_id (str): Unique event identifier.
        emergency_type (EmergencyType): Type of emergency.
        site_id (str): Mine site identifier.
        date_str (str): Event date in 'YYYY-MM-DD' format.
        is_drill (bool): True if planned drill, False if actual incident.
        alarm_to_first_response_min (float): Minutes from alarm to first
            responder arrival at scene. Must be >= 0.
        target_response_time_min (float): Target response time per site
            emergency plan. Must be > 0.
        personnel_on_site (int): Total personnel on site at time of event.
        personnel_mustered (int): Personnel accounted for at muster point.
        muster_window_min (float): Allowable time window for full muster (min).
        time_to_notify_all_stakeholders_min (float): Time from alarm to
            all key contacts notified (safety officer, mine manager, regulator).
        target_notify_time_min (float): Target notification time. Must be > 0.
        corrective_actions_raised (int): Number of corrective actions generated.
        corrective_actions_closed (int): Number closed within due date.

    Example:
        >>> event = EmergencyEvent(
        ...     event_id="EVT-2026-014",
        ...     emergency_type=EmergencyType.DRILL,
        ...     site_id="SITE-KAL-01",
        ...     date_str="2026-03-15",
        ...     is_drill=True,
        ...     alarm_to_first_response_min=8.5,
        ...     target_response_time_min=10.0,
        ...     personnel_on_site=120,
        ...     personnel_mustered=117,
        ...     muster_window_min=15.0,
        ...     time_to_notify_all_stakeholders_min=22.0,
        ...     target_notify_time_min=30.0,
        ...     corrective_actions_raised=5,
        ...     corrective_actions_closed=4,
        ... )
    """

    event_id: str
    emergency_type: EmergencyType
    site_id: str
    date_str: str
    is_drill: bool
    alarm_to_first_response_min: float
    target_response_time_min: float
    personnel_on_site: int
    personnel_mustered: int
    muster_window_min: float
    time_to_notify_all_stakeholders_min: float
    target_notify_time_min: float
    corrective_actions_raised: int
    corrective_actions_closed: int

    def __post_init__(self) -> None:
        if not self.event_id or not self.event_id.strip():
            raise ValueError("event_id cannot be empty.")
        if not self.site_id or not self.site_id.strip():
            raise ValueError("site_id cannot be empty.")
        if self.alarm_to_first_response_min < 0:
            raise ValueError("alarm_to_first_response_min must be >= 0.")
        if self.target_response_time_min <= 0:
            raise ValueError("target_response_time_min must be > 0.")
        if self.personnel_on_site < 0:
            raise ValueError("personnel_on_site must be >= 0.")
        if self.personnel_mustered < 0:
            raise ValueError("personnel_mustered must be >= 0.")
        if self.personnel_mustered > self.personnel_on_site:
            raise ValueError("personnel_mustered cannot exceed personnel_on_site.")
        if self.muster_window_min <= 0:
            raise ValueError("muster_window_min must be > 0.")
        if self.time_to_notify_all_stakeholders_min < 0:
            raise ValueError("time_to_notify_all_stakeholders_min must be >= 0.")
        if self.target_notify_time_min <= 0:
            raise ValueError("target_notify_time_min must be > 0.")
        if self.corrective_actions_raised < 0:
            raise ValueError("corrective_actions_raised must be >= 0.")
        if self.corrective_actions_closed < 0:
            raise ValueError("corrective_actions_closed must be >= 0.")
        if self.corrective_actions_closed > self.corrective_actions_raised:
            raise ValueError(
                "corrective_actions_closed cannot exceed corrective_actions_raised."
            )


@dataclass
class ResponseEvaluationReport:
    """Emergency response evaluation output for one event."""

    event_id: str
    site_id: str
    emergency_type: str
    is_drill: bool
    response_time_index: float          # RTI: target / actual (capped at 1.0)
    muster_completeness_score_pct: float  # MCS: mustered / on_site × 100
    communication_cascade_rate: float   # CCR: target_notify / actual_notify (capped 1.0)
    action_closure_rate_pct: Optional[float]  # ACR: closed / raised × 100
    overall_grade: str
    composite_score: float              # 0–100
    improvement_areas: List[str]
    commendations: List[str]
    regulatory_notification_required: bool
    warnings: List[str] = field(default_factory=list)


class EmergencyResponseEvaluator:
    """
    Evaluate emergency response performance for mining sites.

    Composite score weights:
    - Response Time Index (40%)
    - Muster Completeness Score (35%)
    - Communication Cascade Rate (15%)
    - Action Closure Rate (10%)

    Example:
        >>> evaluator = EmergencyResponseEvaluator()
        >>> event = EmergencyEvent(...)
        >>> report = evaluator.evaluate(event)
        >>> print(f"{report.overall_grade} — Score: {report.composite_score:.1f}")
    """

    # Grade thresholds
    _GRADE_THRESHOLDS = [
        (85.0, ResponseGrade.EXCELLENT),
        (70.0, ResponseGrade.SATISFACTORY),
        (50.0, ResponseGrade.NEEDS_IMPROVEMENT),
        (0.0, ResponseGrade.UNSATISFACTORY),
    ]

    def evaluate(self, event: EmergencyEvent) -> ResponseEvaluationReport:
        """
        Evaluate emergency response performance for one event.

        Args:
            event: EmergencyEvent with response timing and personnel data.

        Returns:
            ResponseEvaluationReport with grade, scores, and recommendations.
        """
        rti = min(
            event.target_response_time_min / max(event.alarm_to_first_response_min, 0.1),
            1.0,
        )
        mcs = (
            event.personnel_mustered / event.personnel_on_site * 100
            if event.personnel_on_site > 0
            else 100.0
        )
        ccr = min(
            event.target_notify_time_min
            / max(event.time_to_notify_all_stakeholders_min, 0.1),
            1.0,
        )
        acr = (
            event.corrective_actions_closed / event.corrective_actions_raised * 100
            if event.corrective_actions_raised > 0
            else None
        )

        composite = self._composite_score(rti, mcs, ccr, acr)
        grade = self._classify_grade(composite)
        improvements = self._improvement_areas(event, rti, mcs, ccr, acr)
        commendations = self._commendations(rti, mcs, ccr)
        notif_required = self._regulatory_notification(event)
        warnings = self._warnings(event, mcs)

        return ResponseEvaluationReport(
            event_id=event.event_id,
            site_id=event.site_id,
            emergency_type=event.emergency_type.value,
            is_drill=event.is_drill,
            response_time_index=round(rti, 3),
            muster_completeness_score_pct=round(mcs, 1),
            communication_cascade_rate=round(ccr, 3),
            action_closure_rate_pct=round(acr, 1) if acr is not None else None,
            overall_grade=grade.value,
            composite_score=round(composite, 1),
            improvement_areas=improvements,
            commendations=commendations,
            regulatory_notification_required=notif_required,
            warnings=warnings,
        )

    def evaluate_site_trend(
        self, events: List[EmergencyEvent]
    ) -> Dict[str, object]:
        """
        Evaluate response performance trend across multiple events at a site.

        Args:
            events: List of EmergencyEvent (same site preferred for trend analysis).

        Returns:
            dict with 'reports', 'average_composite_score', 'trend' ('improving',
            'stable', or 'declining'), and 'grade_distribution'.

        Raises:
            ValueError: If events list is empty.
        """
        if not events:
            raise ValueError("events list cannot be empty.")

        reports = [self.evaluate(e) for e in events]
        scores = [r.composite_score for r in reports]
        avg = sum(scores) / len(scores)

        trend = "stable"
        if len(scores) >= 3:
            first_half = sum(scores[: len(scores) // 2]) / max(len(scores) // 2, 1)
            second_half = sum(scores[len(scores) // 2 :]) / max(len(scores[len(scores) // 2 :]), 1)
            if second_half > first_half + 5.0:
                trend = "improving"
            elif second_half < first_half - 5.0:
                trend = "declining"

        grade_dist: Dict[str, int] = {}
        for r in reports:
            grade_dist[r.overall_grade] = grade_dist.get(r.overall_grade, 0) + 1

        return {
            "reports": reports,
            "average_composite_score": round(avg, 1),
            "trend": trend,
            "grade_distribution": grade_dist,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _composite_score(
        rti: float, mcs: float, ccr: float, acr: Optional[float]
    ) -> float:
        score = rti * 40.0 + (mcs / 100.0) * 35.0 + ccr * 15.0
        if acr is not None:
            score += (acr / 100.0) * 10.0
        else:
            # Redistribute 10% to other metrics proportionally when no actions raised
            score = min(score / 90.0 * 100.0, 100.0)
        return score

    def _classify_grade(self, composite: float) -> ResponseGrade:
        for threshold, grade in self._GRADE_THRESHOLDS:
            if composite >= threshold:
                return grade
        return ResponseGrade.UNSATISFACTORY

    @staticmethod
    def _improvement_areas(
        event: EmergencyEvent,
        rti: float,
        mcs: float,
        ccr: float,
        acr: Optional[float],
    ) -> List[str]:
        areas = []
        if rti < 0.80:
            areas.append(
                f"Response time ({event.alarm_to_first_response_min:.1f} min) exceeded "
                f"target ({event.target_response_time_min:.1f} min) — "
                "review first-responder positioning and alarm coverage."
            )
        if mcs < 95.0:
            unaccounted = event.personnel_on_site - event.personnel_mustered
            areas.append(
                f"{unaccounted} personnel unaccounted for at muster — "
                "enforce buddy-system and improve muster-point signage."
            )
        if ccr < 0.80:
            areas.append(
                f"Stakeholder notification took {event.time_to_notify_all_stakeholders_min:.0f} min "
                f"(target {event.target_notify_time_min:.0f} min) — "
                "update emergency contact cascade and test communication chain quarterly."
            )
        if acr is not None and acr < 80.0:
            open_actions = event.corrective_actions_raised - event.corrective_actions_closed
            areas.append(
                f"{open_actions} corrective actions overdue — "
                "escalate to site manager and assign clear ownership."
            )
        return areas

    @staticmethod
    def _commendations(rti: float, mcs: float, ccr: float) -> List[str]:
        coms = []
        if rti >= 1.0:
            coms.append("Response time met or beat target — excellent first-responder readiness.")
        if mcs >= 100.0:
            coms.append("100% personnel accountability achieved at muster — outstanding.")
        if ccr >= 1.0:
            coms.append("Stakeholder notification completed within target time.")
        return coms

    @staticmethod
    def _regulatory_notification(event: EmergencyEvent) -> bool:
        """Actual incidents (not drills) of high-severity types require regulatory notification."""
        high_severity = {
            EmergencyType.FIRE,
            EmergencyType.EXPLOSION,
            EmergencyType.COLLAPSE,
            EmergencyType.GAS_RELEASE,
        }
        return not event.is_drill and event.emergency_type in high_severity

    @staticmethod
    def _warnings(event: EmergencyEvent, mcs: float) -> List[str]:
        warnings = []
        if mcs < 90.0 and not event.is_drill:
            warnings.append(
                f"ACTUAL INCIDENT: Only {event.personnel_mustered}/{event.personnel_on_site} "
                "personnel accounted for — initiate search protocol immediately."
            )
        if not event.is_drill and event.emergency_type in (
            EmergencyType.EXPLOSION, EmergencyType.COLLAPSE
        ):
            warnings.append(
                "Regulatory notification to ESDM/MSHA required within 15 minutes "
                "of explosion or collapse events."
            )
        return warnings
