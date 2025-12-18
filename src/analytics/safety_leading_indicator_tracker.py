"""
Safety Leading Indicator Tracker for proactive mine safety management.

Leading indicators are proactive, preventive safety metrics that predict
future incident rates before incidents occur. They contrast with lagging
indicators (e.g., LTIFR, TRIFR) which measure outcomes after the fact.

Leading indicators tracked by this module (aligned with ICMM Safety
Leading Indicators Framework 2020 and MSHA best practices):
  1. Safety observation completions (field observation rate vs target)
  2. Near-miss reporting rate (per shift, per crew)
  3. Critical risk control verifications (bow-tie control checks)
  4. Training compliance rate (% workforce current on mandatory training)
  5. Pre-shift inspection completion rate
  6. Toolbox talk delivery rate
  7. Action item close-out rate (corrective actions within due date)

Risk score:
  - Each indicator scored 0–100 (100 = fully meeting target)
  - Composite Safety Health Index (SHI): weighted average
  - Red/Amber/Green (RAG) status per indicator and overall

References:
  - ICMM Leading Indicators for Occupational Safety (2020)
  - MSHA Safety Culture Framework
  - ISO 45001:2018 — Occupational Health and Safety Management Systems

Author: github.com/achmadnaufal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RAGStatus(str, Enum):
    """Red-Amber-Green status for indicator health."""
    GREEN = "GREEN"   # Score ≥ 80
    AMBER = "AMBER"   # Score 60–79
    RED = "RED"       # Score < 60


class IndicatorCategory(str, Enum):
    """Safety leading indicator category."""
    OBSERVATION = "observation"
    REPORTING = "reporting"
    VERIFICATION = "verification"
    TRAINING = "training"
    INSPECTION = "inspection"
    COMMUNICATION = "communication"
    ACTION_MANAGEMENT = "action_management"


# RAG thresholds
RAG_THRESHOLDS: Dict[RAGStatus, float] = {
    RAGStatus.GREEN: 80.0,
    RAGStatus.AMBER: 60.0,
}

# Default weights for composite SHI (sum to 1.0)
DEFAULT_INDICATOR_WEIGHTS: Dict[str, float] = {
    "critical_risk_verifications": 0.25,
    "near_miss_reporting": 0.20,
    "safety_observations": 0.15,
    "training_compliance": 0.15,
    "pre_shift_inspections": 0.10,
    "toolbox_talks": 0.10,
    "action_closeout": 0.05,
}


@dataclass
class LeadingIndicatorRecord:
    """A single period's data for all leading safety indicators.

    Attributes:
        crew_id: Crew or department identifier.
        period: Reporting period (e.g., 'W12-2026').
        site: Mine site name.
        safety_obs_completed: Actual safety observations completed.
        safety_obs_target: Target safety observations for period.
        near_miss_reported: Near-miss reports submitted.
        near_miss_target: Minimum target near-miss reports.
        critical_risk_verifications_completed: Critical risk control checks done.
        critical_risk_verifications_target: Target control checks (bow-tie).
        training_current_count: Workers with current mandatory training sign-off.
        total_workforce: Total workforce headcount.
        pre_shift_inspections_completed: Pre-start inspection forms completed.
        pre_shift_inspections_required: Required pre-start inspections.
        toolbox_talks_delivered: Toolbox talks (safety briefings) delivered.
        toolbox_talks_required: Required toolbox talks per period.
        actions_closed_on_time: Corrective actions closed within due date.
        total_actions_due: Total corrective actions with due date in period.
    """

    crew_id: str
    period: str
    site: str
    safety_obs_completed: int
    safety_obs_target: int
    near_miss_reported: int
    near_miss_target: int
    critical_risk_verifications_completed: int
    critical_risk_verifications_target: int
    training_current_count: int
    total_workforce: int
    pre_shift_inspections_completed: int
    pre_shift_inspections_required: int
    toolbox_talks_delivered: int
    toolbox_talks_required: int
    actions_closed_on_time: int
    total_actions_due: int

    def __post_init__(self) -> None:
        for target_attr in (
            "safety_obs_target", "near_miss_target", "critical_risk_verifications_target",
            "total_workforce", "pre_shift_inspections_required",
            "toolbox_talks_required",
        ):
            if getattr(self, target_attr) <= 0:
                raise ValueError(f"{target_attr} must be positive")
        if self.total_actions_due < 0:
            raise ValueError("total_actions_due cannot be negative")
        for completed_attr, target_attr in [
            ("training_current_count", "total_workforce"),
        ]:
            if getattr(self, completed_attr) > getattr(self, target_attr):
                raise ValueError(f"{completed_attr} cannot exceed {target_attr}")

    # ------------------------------------------------------------------
    # Completion rate properties
    # ------------------------------------------------------------------

    @property
    def safety_obs_rate_pct(self) -> float:
        return min(100.0, (self.safety_obs_completed / self.safety_obs_target) * 100)

    @property
    def near_miss_rate_pct(self) -> float:
        return min(100.0, (self.near_miss_reported / self.near_miss_target) * 100)

    @property
    def critical_risk_verification_rate_pct(self) -> float:
        return min(100.0, (self.critical_risk_verifications_completed / self.critical_risk_verifications_target) * 100)

    @property
    def training_compliance_pct(self) -> float:
        return (self.training_current_count / self.total_workforce) * 100

    @property
    def pre_shift_inspection_rate_pct(self) -> float:
        return min(100.0, (self.pre_shift_inspections_completed / self.pre_shift_inspections_required) * 100)

    @property
    def toolbox_talk_rate_pct(self) -> float:
        return min(100.0, (self.toolbox_talks_delivered / self.toolbox_talks_required) * 100)

    @property
    def action_closeout_rate_pct(self) -> float:
        if self.total_actions_due == 0:
            return 100.0
        return min(100.0, (self.actions_closed_on_time / self.total_actions_due) * 100)


@dataclass
class LeadingIndicatorScore:
    """Scored safety leading indicators for a crew/period.

    Attributes:
        crew_id: Reference crew.
        period: Reporting period.
        site: Mine site.
        indicator_scores: Dict of indicator name → score (0–100).
        indicator_rag: Dict of indicator name → RAGStatus.
        composite_shi: Safety Health Index (weighted composite, 0–100).
        overall_rag: Overall RAG status based on SHI.
        red_indicators: List of indicators in RED status.
        amber_indicators: List of indicators in AMBER status.
        priority_actions: Recommended actions for RED and AMBER indicators.
        trend_vs_last: Optional % change in SHI vs prior period.
    """

    crew_id: str
    period: str
    site: str
    indicator_scores: Dict[str, float]
    indicator_rag: Dict[str, RAGStatus]
    composite_shi: float
    overall_rag: RAGStatus
    red_indicators: List[str]
    amber_indicators: List[str]
    priority_actions: List[str]
    trend_vs_last: Optional[float] = None


class SafetyLeadingIndicatorTracker:
    """Tracks and scores mine safety leading indicators per crew/period.

    Computes a composite Safety Health Index (SHI) and RAG status,
    with prioritised corrective actions for underperforming indicators.

    Example:
        >>> tracker = SafetyLeadingIndicatorTracker()
        >>> record = LeadingIndicatorRecord(
        ...     crew_id="CREW_ALPHA",
        ...     period="W12-2026",
        ...     site="Berau Mine",
        ...     safety_obs_completed=45, safety_obs_target=50,
        ...     near_miss_reported=8, near_miss_target=6,
        ...     critical_risk_verifications_completed=28, critical_risk_verifications_target=30,
        ...     training_current_count=58, total_workforce=62,
        ...     pre_shift_inspections_completed=140, pre_shift_inspections_required=150,
        ...     toolbox_talks_delivered=14, toolbox_talks_required=15,
        ...     actions_closed_on_time=9, total_actions_due=12,
        ... )
        >>> score = tracker.score(record)
        >>> print(score.overall_rag)
        RAGStatus.GREEN
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        green_threshold: float = 80.0,
        amber_threshold: float = 60.0,
    ) -> None:
        """Initialise the tracker.

        Args:
            weights: Optional custom indicator weights (must sum to 1.0).
            green_threshold: Minimum score for GREEN status.
            amber_threshold: Minimum score for AMBER status.
        """
        self.weights = weights or DEFAULT_INDICATOR_WEIGHTS
        self.green_threshold = green_threshold
        self.amber_threshold = amber_threshold
        self._validate_weights()

    def _validate_weights(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Indicator weights must sum to 1.0; got {total:.3f}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        record: LeadingIndicatorRecord,
        prior_shi: Optional[float] = None,
    ) -> LeadingIndicatorScore:
        """Compute leading indicator scores for a crew/period record.

        Args:
            record: LeadingIndicatorRecord with period activity data.
            prior_shi: Prior period SHI for trend calculation (optional).

        Returns:
            LeadingIndicatorScore with SHI, RAG, and priority actions.
        """
        if not isinstance(record, LeadingIndicatorRecord):
            raise TypeError("record must be a LeadingIndicatorRecord instance")

        scores = {
            "safety_observations": record.safety_obs_rate_pct,
            "near_miss_reporting": record.near_miss_rate_pct,
            "critical_risk_verifications": record.critical_risk_verification_rate_pct,
            "training_compliance": record.training_compliance_pct,
            "pre_shift_inspections": record.pre_shift_inspection_rate_pct,
            "toolbox_talks": record.toolbox_talk_rate_pct,
            "action_closeout": record.action_closeout_rate_pct,
        }

        rag_map = {k: self._rag(v) for k, v in scores.items()}

        shi = sum(
            scores.get(indicator, 0) * weight
            for indicator, weight in self.weights.items()
            if indicator in scores
        )
        overall_rag = self._rag(shi)

        reds = [k for k, v in rag_map.items() if v == RAGStatus.RED]
        ambers = [k for k, v in rag_map.items() if v == RAGStatus.AMBER]
        actions = self._generate_actions(record, reds, ambers)

        trend = None
        if prior_shi is not None:
            trend = round(shi - prior_shi, 1)

        return LeadingIndicatorScore(
            crew_id=record.crew_id,
            period=record.period,
            site=record.site,
            indicator_scores={k: round(v, 1) for k, v in scores.items()},
            indicator_rag=rag_map,
            composite_shi=round(shi, 1),
            overall_rag=overall_rag,
            red_indicators=reds,
            amber_indicators=ambers,
            priority_actions=actions,
            trend_vs_last=trend,
        )

    def score_portfolio(
        self, records: List[LeadingIndicatorRecord]
    ) -> List[LeadingIndicatorScore]:
        """Score multiple crew records, sorted by SHI descending.

        Args:
            records: List of LeadingIndicatorRecord.

        Returns:
            Sorted list by composite_shi descending.

        Raises:
            ValueError: If records list is empty.
        """
        if not records:
            raise ValueError("records list cannot be empty")
        scores = [self.score(r) for r in records]
        return sorted(scores, key=lambda s: s.composite_shi, reverse=True)

    def site_summary(self, scores: List[LeadingIndicatorScore]) -> Dict:
        """Aggregate site-level safety health summary.

        Args:
            scores: List of LeadingIndicatorScore.

        Returns:
            Dict with RAG counts, average SHI, and most common red indicator.
        """
        if not scores:
            return {}

        by_rag = {r.value: 0 for r in RAGStatus}
        for s in scores:
            by_rag[s.overall_rag.value] += 1

        avg_shi = sum(s.composite_shi for s in scores) / len(scores)
        all_reds = [ind for s in scores for ind in s.red_indicators]
        top_red = max(set(all_reds), key=all_reds.count) if all_reds else None

        return {
            "total_crews": len(scores),
            "avg_shi": round(avg_shi, 1),
            "rag_distribution": by_rag,
            "crews_red": by_rag.get("RED", 0),
            "most_common_red_indicator": top_red,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rag(self, score: float) -> RAGStatus:
        if score >= self.green_threshold:
            return RAGStatus.GREEN
        elif score >= self.amber_threshold:
            return RAGStatus.AMBER
        return RAGStatus.RED

    @staticmethod
    def _generate_actions(
        record: LeadingIndicatorRecord,
        reds: List[str],
        ambers: List[str],
    ) -> List[str]:
        actions: List[str] = []
        action_map = {
            "critical_risk_verifications": (
                f"URGENT: Critical risk verifications at "
                f"{record.critical_risk_verification_rate_pct:.0f}% — "
                "line manager to conduct unplanned bow-tie control check by end of shift."
            ),
            "near_miss_reporting": (
                f"Near-miss reporting below target ({record.near_miss_reported}/{record.near_miss_target}). "
                "Conduct 'speak up for safety' crew session; check reporting barriers."
            ),
            "safety_observations": (
                f"Safety observations at {record.safety_obs_rate_pct:.0f}%. "
                "Supervisors to complete outstanding observations before period close."
            ),
            "training_compliance": (
                f"Training compliance at {record.training_compliance_pct:.0f}%. "
                f"Schedule {record.total_workforce - record.training_current_count} overdue workers this week."
            ),
            "pre_shift_inspections": (
                "Pre-shift inspection completion below target. "
                "Remind all operators of mandatory pre-start check-sheet requirement."
            ),
            "toolbox_talks": (
                "Toolbox talks below target. "
                "Shift supervisors to deliver outstanding briefings before next shift change."
            ),
            "action_closeout": (
                f"Action close-out at {record.action_closeout_rate_pct:.0f}%. "
                "Review overdue actions with respective owners; escalate to department head."
            ),
        }
        for indicator in reds + ambers:
            if indicator in action_map:
                actions.append(action_map[indicator])
        if not actions:
            actions.append("All leading indicators healthy. Continue current safety engagement.")
        return actions
