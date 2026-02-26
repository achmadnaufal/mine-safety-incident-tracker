"""Unit tests for ShiftHandoverRiskBriefing."""
import pytest
from src.analytics.shift_handover_risk_briefing import (
    ShiftHandoverBriefing, HazardItem, EquipmentFlag, IsolationRecord, ActionItem
)


def _briefing(**kwargs) -> ShiftHandoverBriefing:
    return ShiftHandoverBriefing(
        site=kwargs.get("site", "Pit-A"),
        outgoing_shift=kwargs.get("outgoing_shift", "Day"),
        incoming_shift=kwargs.get("incoming_shift", "Night"),
        date=kwargs.get("date", "2024-06-01"),
    )


def _hazard(hazard_id="HZ-001", risk_level="HIGH", control_status="ACTIVE", **kwargs) -> HazardItem:
    return HazardItem(
        hazard_id=hazard_id,
        description="Test hazard",
        location="Pit-A Bench 3",
        risk_level=risk_level,
        control_status=control_status,
        responsible_person="Foreman A",
        **kwargs,
    )


class TestHazardValidation:
    def test_valid_hazard(self):
        h = _hazard()
        assert h.risk_level == "HIGH"

    def test_invalid_risk_level_raises(self):
        with pytest.raises(ValueError):
            _hazard(risk_level="EXTREME")

    def test_invalid_control_status_raises(self):
        with pytest.raises(ValueError):
            _hazard(control_status="UNKNOWN")

    def test_risk_level_uppercased(self):
        h = _hazard(risk_level="high")
        assert h.risk_level == "HIGH"


class TestEquipmentFlag:
    def test_valid_equipment_flag(self):
        ef = EquipmentFlag(
            equipment_id="CAT-001", description="Hydraulic excavator",
            defect_description="Boom crack", operational_restriction="No heavy loads",
            priority="IMMEDIATE", restricted_use=True
        )
        assert ef.priority == "IMMEDIATE"

    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError):
            EquipmentFlag(
                equipment_id="CAT-001", description="x", defect_description="x",
                operational_restriction="x", priority="URGENT"
            )


class TestBriefingGeneration:
    def test_empty_briefing(self):
        b = _briefing()
        r = b.generate()
        assert r["summary"]["total_hazards"] == 0
        assert r["overall_risk_level"] == "LOW"

    def test_critical_hazard_sets_overall(self):
        b = _briefing()
        b.add_hazard(_hazard(risk_level="CRITICAL"))
        r = b.generate()
        assert r["overall_risk_level"] == "CRITICAL"

    def test_high_hazard_sets_overall_high(self):
        b = _briefing()
        b.add_hazard(_hazard(risk_level="HIGH"))
        r = b.generate()
        assert r["overall_risk_level"] == "HIGH"

    def test_medium_hazard_below_high(self):
        b = _briefing()
        b.add_hazard(_hazard(risk_level="MEDIUM"))
        r = b.generate()
        assert r["overall_risk_level"] == "MEDIUM"

    def test_multiple_hazards_takes_max(self):
        b = _briefing()
        b.add_hazard(_hazard("H1", risk_level="LOW"))
        b.add_hazard(_hazard("H2", risk_level="CRITICAL"))
        r = b.generate()
        assert r["overall_risk_level"] == "CRITICAL"

    def test_critical_alerts_populated(self):
        b = _briefing()
        b.add_hazard(_hazard("HZ-CRIT", risk_level="CRITICAL"))
        r = b.generate()
        assert len(r["critical_alerts"]) == 1

    def test_failed_controls_populated(self):
        b = _briefing()
        b.add_hazard(_hazard("HZ-FC", risk_level="HIGH", control_status="FAILED", critical_control="Berm height"))
        r = b.generate()
        assert len(r["failed_controls"]) == 1

    def test_equipment_flag_in_report(self):
        b = _briefing()
        b.add_equipment_flag(EquipmentFlag(
            equipment_id="EX-01", description="Excavator",
            defect_description="Crack", operational_restriction="No loads",
            priority="IMMEDIATE"
        ))
        r = b.generate()
        assert r["summary"]["immediate_equipment"] == 1

    def test_isolation_in_report(self):
        b = _briefing()
        b.add_isolation(IsolationRecord(
            isolation_id="ISO-01", area_description="North wall",
            reason="Blast exclusion", authorized_by="Mine Manager",
            status="IN_PLACE"
        ))
        r = b.generate()
        assert r["summary"]["active_isolations"] == 1

    def test_open_action_in_report(self):
        b = _briefing()
        b.add_action_item(ActionItem(
            action_id="ACT-01", description="Fix berm",
            owner="Foreman B", priority="HIGH", due="End of shift"
        ))
        r = b.generate()
        assert r["summary"]["open_actions"] == 1

    def test_closed_action_not_in_open(self):
        b = _briefing()
        b.add_action_item(ActionItem(
            action_id="ACT-02", description="Done item",
            owner="Foreman C", priority="LOW", due="Done", status="CLOSED"
        ))
        r = b.generate()
        assert r["summary"]["open_actions"] == 0

    def test_render_text_contains_site(self):
        b = _briefing(site="TestPit")
        b.add_hazard(_hazard())
        text = b.render_text()
        assert "TestPit" in text

    def test_hazards_sorted_by_risk_level(self):
        b = _briefing()
        b.add_hazard(_hazard("LOW-H", risk_level="LOW"))
        b.add_hazard(_hazard("CRIT-H", risk_level="CRITICAL"))
        r = b.generate()
        assert r["hazards"][0]["risk_level"] == "CRITICAL"
