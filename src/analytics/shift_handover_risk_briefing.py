"""
Shift Handover Risk Briefing Generator
==========================================
Produces structured risk briefings for mine shift handovers per ICMM
Critical Control Management and ESDM 1827K/2018 requirements.

Covers:
  - Active hazard carry-over from previous shift
  - Critical control verification status
  - Equipment with deferred maintenance flags
  - Area isolations and exclusion zones
  - Open action items from previous shift

Reference:
  - ICMM (2019) Health and Safety: Critical Control Management Guide
  - Kepmen ESDM 1827K/30/MEM/2018 §§42, 43 — shift inspection requirements
  - MSHA 30 CFR 56.18002 — workplace examination before each shift

Usage::

    from src.analytics.shift_handover_risk_briefing import ShiftHandoverBriefing, HazardItem, EquipmentFlag

    briefing = ShiftHandoverBriefing(
        site="Pit-A",
        outgoing_shift="Day",
        incoming_shift="Night",
        date="2024-06-01",
    )

    briefing.add_hazard(HazardItem(
        hazard_id="HZ-001",
        description="Unstable highwall face at bench 3, north wall",
        location="Pit-A Bench 3 North",
        risk_level="HIGH",
        control_status="ACTIVE",
        responsible_person="Foreman A",
    ))

    report = briefing.generate()
    print(report["overall_risk_level"])   # → HIGH
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_SHIFTS = {"Day", "Night", "Afternoon", "Morning", "Evening"}
VALID_CONTROL_STATUS = {"ACTIVE", "PARTIAL", "FAILED", "PENDING_VERIFICATION"}
VALID_ISOLATION_STATUS = {"IN_PLACE", "REMOVED", "PARTIAL"}

RISK_ESCALATION_MAP = {
    "CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class HazardItem:
    """A carry-over hazard from the outgoing shift."""

    hazard_id: str
    description: str
    location: str
    risk_level: str              # LOW | MEDIUM | HIGH | CRITICAL
    control_status: str          # ACTIVE | PARTIAL | FAILED | PENDING_VERIFICATION
    responsible_person: str
    critical_control: str = ""   # Name of critical control if applicable
    action_required: str = ""
    due_by: str = ""             # Time or next shift target

    def __post_init__(self) -> None:
        self.risk_level = self.risk_level.upper()
        self.control_status = self.control_status.upper()
        if self.risk_level not in VALID_RISK_LEVELS:
            raise ValueError(f"risk_level '{self.risk_level}' invalid. Valid: {sorted(VALID_RISK_LEVELS)}")
        if self.control_status not in VALID_CONTROL_STATUS:
            raise ValueError(f"control_status '{self.control_status}' invalid.")


@dataclass
class EquipmentFlag:
    """Equipment with deferred maintenance or known defects."""

    equipment_id: str
    description: str
    defect_description: str
    operational_restriction: str  # e.g., "No overburden > 30t loads"
    priority: str                 # IMMEDIATE | DEFERRED | MONITOR
    work_order_no: str = ""
    restricted_use: bool = False

    def __post_init__(self) -> None:
        self.priority = self.priority.upper()
        if self.priority not in {"IMMEDIATE", "DEFERRED", "MONITOR"}:
            raise ValueError(f"priority '{self.priority}' invalid.")


@dataclass
class IsolationRecord:
    """Active area isolation or exclusion zone."""

    isolation_id: str
    area_description: str
    reason: str
    authorized_by: str
    status: str        # IN_PLACE | REMOVED | PARTIAL
    expiry: str = ""   # Planned removal time

    def __post_init__(self) -> None:
        self.status = self.status.upper()
        if self.status not in VALID_ISOLATION_STATUS:
            raise ValueError(f"status '{self.status}' invalid.")


@dataclass
class ActionItem:
    """Open action item from previous shift."""

    action_id: str
    description: str
    owner: str
    priority: str    # HIGH | MEDIUM | LOW
    due: str
    status: str = "OPEN"   # OPEN | IN_PROGRESS | CLOSED

    def __post_init__(self) -> None:
        self.priority = self.priority.upper()


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ShiftHandoverBriefing:
    """
    Builds a structured risk briefing for mine shift handovers.

    Methods
    -------
    add_hazard(hazard) — add a carry-over hazard
    add_equipment_flag(flag) — add deferred maintenance flag
    add_isolation(record) — add active isolation/exclusion zone
    add_action_item(item) — add open action item
    generate() — produce the full briefing dict
    render_text() — human-readable text version
    """

    def __init__(self, site: str, outgoing_shift: str, incoming_shift: str, date: str) -> None:
        self.site = site
        self.outgoing_shift = outgoing_shift
        self.incoming_shift = incoming_shift
        self.date = date
        self._hazards: list[HazardItem] = []
        self._equipment: list[EquipmentFlag] = []
        self._isolations: list[IsolationRecord] = []
        self._actions: list[ActionItem] = []

    def add_hazard(self, hazard: HazardItem) -> None:
        self._hazards.append(hazard)

    def add_equipment_flag(self, flag: EquipmentFlag) -> None:
        self._equipment.append(flag)

    def add_isolation(self, record: IsolationRecord) -> None:
        self._isolations.append(record)

    def add_action_item(self, item: ActionItem) -> None:
        self._actions.append(item)

    # ------------------------------------------------------------------
    # Generate briefing
    # ------------------------------------------------------------------

    def generate(self) -> dict:
        """Generate the full structured risk briefing."""
        overall_risk = self._overall_risk()
        critical_controls_failed = [
            h for h in self._hazards
            if h.control_status == "FAILED" and h.critical_control
        ]
        critical_hazards = [h for h in self._hazards if h.risk_level == "CRITICAL"]
        immediate_equipment = [e for e in self._equipment if e.priority == "IMMEDIATE"]
        active_isolations = [i for i in self._isolations if i.status == "IN_PLACE"]
        open_actions = [a for a in self._actions if a.status in {"OPEN", "IN_PROGRESS"}]

        return {
            "site": self.site,
            "date": self.date,
            "outgoing_shift": self.outgoing_shift,
            "incoming_shift": self.incoming_shift,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "overall_risk_level": overall_risk,
            "summary": {
                "total_hazards": len(self._hazards),
                "critical_hazards": len(critical_hazards),
                "high_hazards": sum(1 for h in self._hazards if h.risk_level == "HIGH"),
                "failed_critical_controls": len(critical_controls_failed),
                "equipment_flags": len(self._equipment),
                "immediate_equipment": len(immediate_equipment),
                "active_isolations": len(active_isolations),
                "open_actions": len(open_actions),
            },
            "critical_alerts": [
                {"hazard_id": h.hazard_id, "description": h.description, "location": h.location,
                 "control_status": h.control_status}
                for h in critical_hazards
            ],
            "failed_controls": [
                {"hazard_id": h.hazard_id, "critical_control": h.critical_control,
                 "location": h.location, "responsible": h.responsible_person}
                for h in critical_controls_failed
            ],
            "hazards": [
                {
                    "hazard_id": h.hazard_id,
                    "risk_level": h.risk_level,
                    "description": h.description,
                    "location": h.location,
                    "control_status": h.control_status,
                    "action_required": h.action_required,
                    "responsible": h.responsible_person,
                }
                for h in sorted(self._hazards, key=lambda x: -RISK_ESCALATION_MAP.get(x.risk_level, 0))
            ],
            "equipment_flags": [
                {
                    "equipment_id": e.equipment_id,
                    "defect": e.defect_description,
                    "restriction": e.operational_restriction,
                    "priority": e.priority,
                    "work_order": e.work_order_no,
                    "restricted_use": e.restricted_use,
                }
                for e in self._equipment
            ],
            "isolations": [
                {
                    "isolation_id": i.isolation_id,
                    "area": i.area_description,
                    "reason": i.reason,
                    "authorized_by": i.authorized_by,
                    "status": i.status,
                    "expiry": i.expiry,
                }
                for i in self._isolations
            ],
            "open_actions": [
                {
                    "action_id": a.action_id,
                    "description": a.description,
                    "owner": a.owner,
                    "priority": a.priority,
                    "due": a.due,
                    "status": a.status,
                }
                for a in open_actions
            ],
        }

    def render_text(self) -> str:
        """Produce a text-format briefing suitable for a shift handover form."""
        b = self.generate()
        lines = [
            f"{'='*60}",
            f"SHIFT HANDOVER RISK BRIEFING",
            f"Site: {b['site']} | Date: {b['date']}",
            f"Outgoing: {b['outgoing_shift']} Shift → Incoming: {b['incoming_shift']} Shift",
            f"Overall Risk Level: *** {b['overall_risk_level']} ***",
            f"{'='*60}",
            "",
            "SUMMARY",
            f"  Hazards: {b['summary']['total_hazards']} total "
            f"({b['summary']['critical_hazards']} CRITICAL, {b['summary']['high_hazards']} HIGH)",
            f"  Failed Critical Controls: {b['summary']['failed_critical_controls']}",
            f"  Equipment Flags: {b['summary']['equipment_flags']} "
            f"({b['summary']['immediate_equipment']} IMMEDIATE)",
            f"  Active Isolations: {b['summary']['active_isolations']}",
            f"  Open Actions: {b['summary']['open_actions']}",
            "",
        ]

        if b["critical_alerts"]:
            lines.append("⚠ CRITICAL ALERTS (STOP-WORK REVIEW REQUIRED)")
            for alert in b["critical_alerts"]:
                lines.append(f"  [{alert['hazard_id']}] {alert['description']} @ {alert['location']}")
            lines.append("")

        if b["failed_controls"]:
            lines.append("❌ FAILED CRITICAL CONTROLS")
            for fc in b["failed_controls"]:
                lines.append(f"  [{fc['hazard_id']}] Control: {fc['critical_control']} | Responsible: {fc['responsible']}")
            lines.append("")

        lines.append("HAZARDS (highest risk first)")
        for h in b["hazards"]:
            lines.append(f"  [{h['risk_level']}] {h['hazard_id']}: {h['description']} @ {h['location']}")
            if h["action_required"]:
                lines.append(f"    → Action: {h['action_required']}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _overall_risk(self) -> str:
        """Overall shift risk = highest single hazard risk level, or MEDIUM if any equipment flags."""
        if not self._hazards and not self._equipment:
            return "LOW"
        max_risk = 0
        for h in self._hazards:
            max_risk = max(max_risk, RISK_ESCALATION_MAP.get(h.risk_level, 0))
        for e in self._equipment:
            if e.priority == "IMMEDIATE":
                max_risk = max(max_risk, RISK_ESCALATION_MAP["HIGH"])
        for level, score in RISK_ESCALATION_MAP.items():
            if score == max_risk:
                return level
        return "LOW"
