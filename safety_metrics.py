"""Mining safety performance metrics module.

Provides :class:`SafetyMetricsCalculator` for computing standard mining
industry KPIs (TRIFR, LTIFR, fatality rate, near-miss ratio) and a
qualitative safety-culture assessment.

References:
    - ICMM Safety Performance Framework (2021)
    - Queensland Coal Mining Safety and Health Regulation 2017
    - ISO 45001:2018 Occupational Health and Safety Management Systems

Example::

    from safety_metrics import SafetyMetricsCalculator

    calc = SafetyMetricsCalculator(
        mine_name="Kalimantan Coal Mine",
        total_hours_worked=1_500_000,
        fatalities=0,
        lost_time_injuries=3,
        medical_treatments=8,
        near_misses=45,
    )
    print(calc.analyze())
"""

from __future__ import annotations

from typing import Dict
from enum import Enum


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------


class SeverityLevel(Enum):
    """Incident severity classification aligned with ICMM definitions.

    Attributes:
        FATALITY: A work-related death.
        LOST_TIME_INJURY: Injury causing at least one full shift lost.
        MEDICAL_TREATMENT: Injury requiring treatment beyond first aid.
        NEAR_MISS: Unplanned event with potential to cause harm.
    """

    FATALITY = "fatality"
    LOST_TIME_INJURY = "lost_time_injury"
    MEDICAL_TREATMENT = "medical_treatment"
    NEAR_MISS = "near_miss"


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------


class SafetyMetricsCalculator:
    """Calculate mining safety KPIs and incident rates.

    All frequency rates are expressed *per one million hours worked* to
    align with ICMM and Queensland reporting conventions.

    Args:
        mine_name: Human-readable mine or site name used in reports.
        total_hours_worked: Total exposure hours in the reporting period.
            Must be a positive integer.
        fatalities: Number of fatalities (default 0).
        lost_time_injuries: Number of lost-time injuries (default 0).
        medical_treatments: Number of medical-treatment injuries (default 0).
        near_misses: Number of near-miss events reported (default 0).

    Raises:
        ValueError: If ``total_hours_worked`` is not positive, or if any
            incident count is negative, or if ``mine_name`` is blank.

    Example::

        calc = SafetyMetricsCalculator(
            mine_name="Berau Coal Pit-B",
            total_hours_worked=800_000,
            lost_time_injuries=2,
            near_misses=30,
        )
        result = calc.analyze()
    """

    def __init__(
        self,
        mine_name: str,
        total_hours_worked: int,
        fatalities: int = 0,
        lost_time_injuries: int = 0,
        medical_treatments: int = 0,
        near_misses: int = 0,
    ) -> None:
        if not mine_name or not mine_name.strip():
            raise ValueError("mine_name must not be blank.")
        if total_hours_worked <= 0:
            raise ValueError(
                f"total_hours_worked must be positive; got {total_hours_worked}."
            )
        counts = {
            "fatalities": fatalities,
            "lost_time_injuries": lost_time_injuries,
            "medical_treatments": medical_treatments,
            "near_misses": near_misses,
        }
        for field, value in counts.items():
            if value < 0:
                raise ValueError(
                    f"Incident counts must be non-negative; {field}={value}."
                )

        self.mine_name: str = mine_name
        self.total_hours_worked: int = total_hours_worked
        self.fatalities: int = fatalities
        self.lost_time_injuries: int = lost_time_injuries
        self.medical_treatments: int = medical_treatments
        self.near_misses: int = near_misses

    # ------------------------------------------------------------------
    # KPI calculations
    # ------------------------------------------------------------------

    def calculate_trifr(self) -> float:
        """Calculate Total Recordable Incident Frequency Rate (per 1 M hours).

        TRIFR includes fatalities, lost-time injuries, and medical-treatment
        injuries.

        Returns:
            TRIFR as a float.
        """
        total_incidents = (
            self.fatalities + self.lost_time_injuries + self.medical_treatments
        )
        return (total_incidents / self.total_hours_worked) * 1_000_000

    def calculate_ltifr(self) -> float:
        """Calculate Lost Time Injury Frequency Rate (per 1 M hours).

        LTIFR includes fatalities and lost-time injuries only.

        Returns:
            LTIFR as a float.
        """
        total_lti = self.fatalities + self.lost_time_injuries
        return (total_lti / self.total_hours_worked) * 1_000_000

    def calculate_fatality_rate(self) -> float:
        """Calculate fatality rate per 1 M hours worked.

        Returns:
            Fatality rate as a float.
        """
        return (self.fatalities / self.total_hours_worked) * 1_000_000

    def calculate_near_miss_ratio(self) -> float:
        """Calculate the near-miss to LTI ratio.

        A high ratio (> 10) indicates a proactive safety reporting culture.
        A ratio of zero with non-zero near misses returns ``inf``.

        Returns:
            Near-miss ratio (near_misses / (fatalities + lost_time_injuries)).
            Returns ``0.0`` when both near misses and LTIs are zero.
        """
        lti = self.lost_time_injuries + self.fatalities
        if lti == 0:
            return 0.0 if self.near_misses == 0 else float("inf")
        return self.near_misses / lti

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------

    def assess_safety_culture(self) -> str:
        """Assess mine safety culture based on computed metrics.

        Assessment logic:

        - ``"excellent"`` – TRIFR < 5 **and** near-miss ratio > 10
        - ``"good"`` – TRIFR < 10 **and** near-miss ratio > 5
        - ``"adequate"`` – TRIFR < 20
        - ``"poor"`` – TRIFR >= 20

        Returns:
            One of ``"excellent"``, ``"good"``, ``"adequate"``, or ``"poor"``.
        """
        trifr = self.calculate_trifr()
        near_miss_ratio = self.calculate_near_miss_ratio()

        if trifr < 5 and near_miss_ratio > 10:
            return "excellent"
        if trifr < 10 and near_miss_ratio > 5:
            return "good"
        if trifr < 20:
            return "adequate"
        return "poor"

    def analyze(self) -> Dict[str, object]:
        """Generate a comprehensive safety analysis report.

        Returns:
            Dict containing all input counts and computed KPIs:

            - ``mine_name``
            - ``total_hours_worked``
            - ``fatalities``, ``lost_time_injuries``, ``medical_treatments``,
              ``near_misses``
            - ``trifr`` – Total Recordable Incident Frequency Rate
            - ``ltifr`` – Lost Time Injury Frequency Rate
            - ``fatality_rate_per_1m`` – Fatality rate per 1 M hours
            - ``near_miss_ratio`` – Near-miss to LTI ratio
            - ``safety_culture`` – Qualitative culture assessment
        """
        return {
            "mine_name": self.mine_name,
            "total_hours_worked": self.total_hours_worked,
            "fatalities": self.fatalities,
            "lost_time_injuries": self.lost_time_injuries,
            "medical_treatments": self.medical_treatments,
            "near_misses": self.near_misses,
            "trifr": round(self.calculate_trifr(), 2),
            "ltifr": round(self.calculate_ltifr(), 2),
            "fatality_rate_per_1m": round(self.calculate_fatality_rate(), 2),
            "near_miss_ratio": round(self.calculate_near_miss_ratio(), 2),
            "safety_culture": self.assess_safety_culture(),
        }
