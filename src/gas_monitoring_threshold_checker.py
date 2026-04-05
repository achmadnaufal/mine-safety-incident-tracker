"""
Gas Monitoring Threshold Checker
===================================
Evaluates underground/open-cut mine gas readings against regulatory
and industry threshold limits, generating alerts and evacuation decisions.

Gases monitored:
 - CH₄ (methane) — explosion risk
 - CO (carbon monoxide) — toxic gas, fire indicator
 - CO₂ (carbon dioxide) — asphyxiation risk
 - O₂ (oxygen) — deficiency / enrichment
 - H₂S (hydrogen sulfide) — toxic gas
 - NO₂ (nitrogen dioxide) — blasting fumes
 - SO₂ (sulfur dioxide) — spontaneous combustion indicator

Standards referenced:
 - Australian Coal Mine Safety & Health Regulation 2017 (Qld)
 - US MSHA 30 CFR Part 75 (underground coal mines)
 - Indonesian Kepmen ESDM No. 1827 K/30/MEM/2018
 - NIOSH RELs for mining environments

Alert levels:
 - LEVEL_1 (Advisory): approach limit, increase monitoring frequency
 - LEVEL_2 (Warning): near action limit, investigate source
 - LEVEL_3 (Action): mandatory response, restrict personnel
 - LEVEL_4 (Evacuation): immediate withdrawal of all personnel
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class GasType(str, Enum):
    CH4 = "CH4"
    CO = "CO"
    CO2 = "CO2"
    O2 = "O2"
    H2S = "H2S"
    NO2 = "NO2"
    SO2 = "SO2"


class AlertLevel(str, Enum):
    NORMAL = "NORMAL"
    LEVEL_1 = "LEVEL_1_ADVISORY"
    LEVEL_2 = "LEVEL_2_WARNING"
    LEVEL_3 = "LEVEL_3_ACTION"
    LEVEL_4 = "LEVEL_4_EVACUATION"


class MineType(str, Enum):
    UNDERGROUND_COAL = "underground_coal"
    OPEN_CUT_COAL = "open_cut_coal"
    UNDERGROUND_METAL = "underground_metal"


@dataclass
class GasThreshold:
    """Threshold definition for a single gas."""
    gas: GasType
    unit: str             # "ppm" or "% v/v"
    advisory: float       # Level 1
    warning: float        # Level 2
    action: float         # Level 3
    evacuation: float     # Level 4
    twas_ppm: Optional[float] = None   # time-weighted average standard (8 hr)
    stel_ppm: Optional[float] = None   # short-term exposure limit (15 min)


@dataclass
class GasReading:
    """Single gas sensor reading."""
    sensor_id: str
    location: str
    timestamp: datetime
    gas: GasType
    value: float
    unit: str

    def __post_init__(self):
        if self.value < 0:
            raise ValueError(f"Gas reading value must be >= 0, got {self.value}")


@dataclass
class GasAlert:
    """Alert generated from a gas reading."""
    sensor_id: str
    location: str
    timestamp: datetime
    gas: GasType
    measured_value: float
    unit: str
    alert_level: AlertLevel
    threshold_exceeded: float
    mandatory_action: str
    escalation_time_min: Optional[int] = None  # minutes to escalate if not addressed


@dataclass
class MonitoringReport:
    """Aggregated monitoring report for a shift or time window."""
    site_id: str
    mine_type: MineType
    period_start: datetime
    period_end: datetime
    total_readings: int
    alerts_by_level: Dict[str, int]
    highest_alert_level: AlertLevel
    location_summaries: Dict[str, Dict]
    evacuation_required: bool
    compliance_status: str  # "COMPLIANT", "NON-COMPLIANT"
    recommendations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Threshold tables (per MineType)
# ---------------------------------------------------------------------------

# Underground coal: Australian Qld Coal Mining Safety and Health Regulation 2017
_THRESHOLDS_UNDERGROUND_COAL: Dict[GasType, GasThreshold] = {
    GasType.CH4: GasThreshold(GasType.CH4, "% v/v", 0.25, 0.5, 1.0, 1.25),
    GasType.CO: GasThreshold(GasType.CO, "ppm", 25, 50, 100, 400, twas_ppm=25, stel_ppm=200),
    GasType.CO2: GasThreshold(GasType.CO2, "% v/v", 0.5, 1.0, 1.5, 3.0),
    GasType.O2: GasThreshold(GasType.O2, "% v/v", 20.0, 19.5, 19.0, 17.0),   # deficiency (lower is worse)
    GasType.H2S: GasThreshold(GasType.H2S, "ppm", 5, 10, 20, 50, twas_ppm=1, stel_ppm=5),
    GasType.NO2: GasThreshold(GasType.NO2, "ppm", 1, 2, 3, 5, twas_ppm=0.2, stel_ppm=1),
    GasType.SO2: GasThreshold(GasType.SO2, "ppm", 1, 2, 5, 10, twas_ppm=0.5, stel_ppm=2),
}

# Open-cut coal: slightly relaxed thresholds (ventilation better)
_THRESHOLDS_OPEN_CUT: Dict[GasType, GasThreshold] = {
    GasType.CH4: GasThreshold(GasType.CH4, "% v/v", 0.5, 1.0, 1.5, 2.0),
    GasType.CO: GasThreshold(GasType.CO, "ppm", 50, 100, 200, 400, twas_ppm=25, stel_ppm=200),
    GasType.CO2: GasThreshold(GasType.CO2, "% v/v", 1.0, 2.0, 3.0, 5.0),
    GasType.O2: GasThreshold(GasType.O2, "% v/v", 20.0, 19.5, 19.0, 17.0),
    GasType.H2S: GasThreshold(GasType.H2S, "ppm", 5, 10, 20, 50),
    GasType.NO2: GasThreshold(GasType.NO2, "ppm", 1, 2, 3, 5),
    GasType.SO2: GasThreshold(GasType.SO2, "ppm", 2, 5, 10, 20),
}

_THRESHOLDS: Dict[MineType, Dict[GasType, GasThreshold]] = {
    MineType.UNDERGROUND_COAL: _THRESHOLDS_UNDERGROUND_COAL,
    MineType.OPEN_CUT_COAL: _THRESHOLDS_OPEN_CUT,
    MineType.UNDERGROUND_METAL: _THRESHOLDS_OPEN_CUT,  # simplified
}

# O₂ is inverse: lower reading = higher risk
_INVERSE_GAS = {GasType.O2}

_MANDATORY_ACTIONS: Dict[AlertLevel, str] = {
    AlertLevel.NORMAL: "No action required. Continue routine monitoring.",
    AlertLevel.LEVEL_1: "Advisory: Increase monitoring frequency to 5-minute intervals. Log in shift report.",
    AlertLevel.LEVEL_2: "Warning: Notify Undermanager. Investigate source immediately. Prepare for personnel restriction.",
    AlertLevel.LEVEL_3: "Action Required: Restrict personnel within 50 m. Notify Mine Manager. Commence source investigation.",
    AlertLevel.LEVEL_4: "EVACUATION: Immediately withdraw ALL personnel from affected area. Sound alarm. Notify Inspector of Mines.",
}

_ESCALATION_TIMES: Dict[AlertLevel, Optional[int]] = {
    AlertLevel.NORMAL: None,
    AlertLevel.LEVEL_1: 60,
    AlertLevel.LEVEL_2: 30,
    AlertLevel.LEVEL_3: 10,
    AlertLevel.LEVEL_4: None,  # immediate
}


class GasMonitoringThresholdChecker:
    """
    Evaluates gas sensor readings against regulatory thresholds.

    Examples
    --------
    >>> from mine_safety_incident_tracker.src.gas_monitoring_threshold_checker import (
    ...     GasMonitoringThresholdChecker, GasReading, GasType, MineType
    ... )
    >>> from datetime import datetime
    >>> checker = GasMonitoringThresholdChecker(MineType.UNDERGROUND_COAL)
    >>> reading = GasReading(
    ...     sensor_id="CH4-07", location="13 Heading", timestamp=datetime.now(),
    ...     gas=GasType.CH4, value=0.8, unit="% v/v"
    ... )
    >>> alert = checker.check_reading(reading)
    >>> alert.alert_level.value
    'LEVEL_3_ACTION'
    """

    def __init__(self, mine_type: MineType = MineType.UNDERGROUND_COAL):
        self.mine_type = mine_type
        self.thresholds = _THRESHOLDS[mine_type]

    def _alert_level_for_gas(self, gas: GasType, value: float) -> AlertLevel:
        """Determine alert level for a single gas reading."""
        thresh = self.thresholds.get(gas)
        if thresh is None:
            return AlertLevel.NORMAL

        if gas in _INVERSE_GAS:
            # O₂: lower = worse
            if value <= thresh.evacuation:
                return AlertLevel.LEVEL_4
            elif value <= thresh.action:
                return AlertLevel.LEVEL_3
            elif value <= thresh.warning:
                return AlertLevel.LEVEL_2
            elif value <= thresh.advisory:
                return AlertLevel.LEVEL_1
            else:
                return AlertLevel.NORMAL
        else:
            # Standard: higher = worse
            if value >= thresh.evacuation:
                return AlertLevel.LEVEL_4
            elif value >= thresh.action:
                return AlertLevel.LEVEL_3
            elif value >= thresh.warning:
                return AlertLevel.LEVEL_2
            elif value >= thresh.advisory:
                return AlertLevel.LEVEL_1
            else:
                return AlertLevel.NORMAL

    def check_reading(self, reading: GasReading) -> GasAlert:
        """
        Check a single gas reading and return an alert.

        Parameters
        ----------
        reading : GasReading

        Returns
        -------
        GasAlert
        """
        alert_level = self._alert_level_for_gas(reading.gas, reading.value)
        thresh = self.thresholds.get(reading.gas)
        threshold_exceeded = (
            thresh.advisory if thresh else 0.0
        )

        # Find the exact threshold crossed
        if thresh:
            if reading.gas in _INVERSE_GAS:
                for level, t_val in [
                    (AlertLevel.LEVEL_4, thresh.evacuation),
                    (AlertLevel.LEVEL_3, thresh.action),
                    (AlertLevel.LEVEL_2, thresh.warning),
                    (AlertLevel.LEVEL_1, thresh.advisory),
                ]:
                    if alert_level == level:
                        threshold_exceeded = t_val
                        break
            else:
                for level, t_val in [
                    (AlertLevel.LEVEL_4, thresh.evacuation),
                    (AlertLevel.LEVEL_3, thresh.action),
                    (AlertLevel.LEVEL_2, thresh.warning),
                    (AlertLevel.LEVEL_1, thresh.advisory),
                ]:
                    if alert_level == level:
                        threshold_exceeded = t_val
                        break

        return GasAlert(
            sensor_id=reading.sensor_id,
            location=reading.location,
            timestamp=reading.timestamp,
            gas=reading.gas,
            measured_value=reading.value,
            unit=reading.unit,
            alert_level=alert_level,
            threshold_exceeded=threshold_exceeded,
            mandatory_action=_MANDATORY_ACTIONS[alert_level],
            escalation_time_min=_ESCALATION_TIMES[alert_level],
        )

    def check_readings_batch(self, readings: List[GasReading]) -> List[GasAlert]:
        """Check multiple readings; return alert for each."""
        return [self.check_reading(r) for r in readings]

    def generate_shift_report(
        self,
        site_id: str,
        readings: List[GasReading],
        period_start: datetime,
        period_end: datetime,
    ) -> MonitoringReport:
        """
        Generate a monitoring report for a shift period.

        Parameters
        ----------
        site_id : str
        readings : List[GasReading]
        period_start, period_end : datetime

        Returns
        -------
        MonitoringReport
        """
        if not readings:
            raise ValueError("readings list must not be empty for shift report")

        alerts = self.check_readings_batch(readings)

        # Count by level
        level_counts = {
            "NORMAL": 0, "LEVEL_1_ADVISORY": 0, "LEVEL_2_WARNING": 0,
            "LEVEL_3_ACTION": 0, "LEVEL_4_EVACUATION": 0
        }
        for a in alerts:
            level_counts[a.alert_level.value] = level_counts.get(a.alert_level.value, 0) + 1

        # Highest alert level
        level_priority = {
            AlertLevel.NORMAL: 0, AlertLevel.LEVEL_1: 1, AlertLevel.LEVEL_2: 2,
            AlertLevel.LEVEL_3: 3, AlertLevel.LEVEL_4: 4,
        }
        highest = max(alerts, key=lambda a: level_priority.get(a.alert_level, 0))

        # Location summaries
        loc_summaries: Dict[str, Dict] = {}
        for a in alerts:
            if a.location not in loc_summaries:
                loc_summaries[a.location] = {"readings": 0, "max_alert": AlertLevel.NORMAL}
            loc_summaries[a.location]["readings"] += 1
            if level_priority[a.alert_level] > level_priority[loc_summaries[a.location]["max_alert"]]:
                loc_summaries[a.location]["max_alert"] = a.alert_level

        evacuation_required = highest.alert_level == AlertLevel.LEVEL_4
        non_compliant = highest.alert_level.value in ("LEVEL_3_ACTION", "LEVEL_4_EVACUATION")
        compliance_status = "NON-COMPLIANT" if non_compliant else "COMPLIANT"

        recommendations = self._recommendations(alerts)

        return MonitoringReport(
            site_id=site_id,
            mine_type=self.mine_type,
            period_start=period_start,
            period_end=period_end,
            total_readings=len(readings),
            alerts_by_level=level_counts,
            highest_alert_level=highest.alert_level,
            location_summaries={k: {"readings": v["readings"], "max_alert": v["max_alert"].value}
                                  for k, v in loc_summaries.items()},
            evacuation_required=evacuation_required,
            compliance_status=compliance_status,
            recommendations=recommendations,
        )

    def _recommendations(self, alerts: List[GasAlert]) -> List[str]:
        """Generate actionable recommendations from alert set."""
        recs = []
        gases_at_action = {a.gas for a in alerts
                           if a.alert_level in (AlertLevel.LEVEL_3, AlertLevel.LEVEL_4)}
        if GasType.CH4 in gases_at_action:
            recs.append("CH₄ at action level — check longwall goaf, seals, and ventilation fan operation")
        if GasType.CO in gases_at_action:
            recs.append("CO elevated — potential spontaneous combustion event; deploy inspection team")
        if GasType.H2S in gases_at_action:
            recs.append("H₂S at action level — issue SCBA to personnel; check geological strata intrusion")
        if GasType.O2 in gases_at_action:
            recs.append("O₂ deficiency at action level — check auxiliary ventilation; issue BA sets")
        if not recs:
            recs.append("No critical gas exceedances this shift. Maintain routine monitoring schedule.")
        return recs
