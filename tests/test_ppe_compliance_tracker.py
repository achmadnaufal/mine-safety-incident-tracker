"""
Unit tests for PPEComplianceTracker.
"""

import pytest
from src.analytics.ppe_compliance_tracker import (
    PPEComplianceTracker,
    InspectionRecord,
    ComplianceScore,
    VALID_ZONES,
    ALL_PPE_ITEMS,
    _ZONE_REQUIREMENTS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker():
    return PPEComplianceTracker(site_id="KALTIM-01", zone="open_cut", minimum_compliance_threshold_pct=95.0)


@pytest.fixture
def full_record():
    return InspectionRecord(
        worker_id="W-001",
        date="2026-03-30",
        ppe_worn=["head", "foot", "eye", "hearing", "body"],
        zone="open_cut",
        inspector_id="INS-01",
    )


@pytest.fixture
def partial_record():
    return InspectionRecord(
        worker_id="W-002",
        date="2026-03-30",
        ppe_worn=["head", "foot"],   # missing eye, hearing, body
        zone="open_cut",
        inspector_id="INS-01",
    )


# ---------------------------------------------------------------------------
# InspectionRecord validation
# ---------------------------------------------------------------------------

class TestInspectionRecord:
    def test_valid_creation(self, full_record):
        assert full_record.worker_id == "W-001"

    def test_empty_worker_id_raises(self):
        with pytest.raises(ValueError, match="worker_id"):
            InspectionRecord("", "2026-03-30", ["head"], "open_cut")

    def test_invalid_zone_raises(self):
        with pytest.raises(ValueError, match="zone"):
            InspectionRecord("W-1", "2026-03-30", ["head"], "office")

    def test_unknown_ppe_raises(self):
        with pytest.raises(ValueError, match="Unknown PPE item"):
            InspectionRecord("W-1", "2026-03-30", ["helmet"], "open_cut")  # "helmet" not valid

    def test_invalid_shift_raises(self):
        with pytest.raises(ValueError, match="shift"):
            InspectionRecord("W-1", "2026-03-30", ["head"], "open_cut", shift="evening")

    def test_all_valid_ppe_items_accepted(self):
        r = InspectionRecord("W-1", "2026-03-30", list(ALL_PPE_ITEMS), "underground")
        assert set(r.ppe_worn) == ALL_PPE_ITEMS


# ---------------------------------------------------------------------------
# Tracker instantiation
# ---------------------------------------------------------------------------

class TestTrackerInstantiation:
    def test_valid_creation(self, tracker):
        assert tracker.site_id == "KALTIM-01"

    def test_empty_site_id_raises(self):
        with pytest.raises(ValueError, match="site_id"):
            PPEComplianceTracker("")

    def test_invalid_zone_raises(self):
        with pytest.raises(ValueError, match="zone"):
            PPEComplianceTracker("SITE-01", zone="office")

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            PPEComplianceTracker("SITE-01", minimum_compliance_threshold_pct=0.0)

    def test_all_valid_zones(self):
        for z in VALID_ZONES:
            t = PPEComplianceTracker("X", zone=z)
            assert t.zone == z


# ---------------------------------------------------------------------------
# log_inspection
# ---------------------------------------------------------------------------

class TestLogInspection:
    def test_returns_compliance_score(self, tracker, full_record):
        s = tracker.log_inspection(full_record)
        assert isinstance(s, ComplianceScore)

    def test_full_compliance_no_missing(self, tracker, full_record):
        s = tracker.log_inspection(full_record)
        assert s.full_compliance is True
        assert s.missing_ppe == []

    def test_partial_compliance(self, tracker, partial_record):
        s = tracker.log_inspection(partial_record)
        assert s.full_compliance is False
        assert len(s.missing_ppe) > 0

    def test_missing_ppe_identified(self, tracker, partial_record):
        s = tracker.log_inspection(partial_record)
        assert "eye" in s.missing_ppe
        assert "hearing" in s.missing_ppe
        assert "body" in s.missing_ppe

    def test_weighted_score_100_for_full_compliance(self, tracker, full_record):
        s = tracker.log_inspection(full_record)
        assert s.weighted_score == pytest.approx(100.0)

    def test_weighted_score_below_100_for_partial(self, tracker, partial_record):
        s = tracker.log_inspection(partial_record)
        assert s.weighted_score < 100.0

    def test_extra_ppe_recorded(self, tracker):
        r = InspectionRecord("W-3", "2026-03-30", ["head", "foot", "eye", "hearing", "body", "hand"], "open_cut")
        s = tracker.log_inspection(r)
        assert "hand" in s.extra_ppe

    def test_record_count_increases(self, tracker, full_record):
        assert tracker.total_inspections == 0
        tracker.log_inspection(full_record)
        assert tracker.total_inspections == 1

    def test_clear_removes_records(self, tracker, full_record):
        tracker.log_inspection(full_record)
        tracker.clear()
        assert tracker.total_inspections == 0


# ---------------------------------------------------------------------------
# Risk levels
# ---------------------------------------------------------------------------

class TestRiskLevels:
    def test_full_compliance_ok(self, tracker, full_record):
        s = tracker.log_inspection(full_record)
        assert s.risk_level == "OK"

    def test_missing_head_critical(self, tracker):
        r = InspectionRecord("W-4", "2026-03-30", ["foot", "eye", "hearing", "body"], "open_cut")
        s = tracker.log_inspection(r)
        assert s.risk_level == "CRITICAL"

    def test_missing_foot_high(self, tracker):
        r = InspectionRecord("W-5", "2026-03-30", ["head", "eye", "hearing", "body"], "open_cut")
        s = tracker.log_inspection(r)
        assert s.risk_level == "HIGH"

    def test_missing_body_low_or_moderate(self, tracker):
        r = InspectionRecord("W-6", "2026-03-30", ["head", "foot", "eye", "hearing"], "open_cut")
        s = tracker.log_inspection(r)
        assert s.risk_level in ("LOW", "MODERATE")

    def test_missing_respiratory_underground_critical(self, tracker):
        r = InspectionRecord("W-7", "2026-03-30", ["head", "foot", "eye", "hearing", "body"], "underground")
        s = tracker.log_inspection(r)
        assert s.risk_level == "CRITICAL"


# ---------------------------------------------------------------------------
# daily_report
# ---------------------------------------------------------------------------

class TestDailyReport:
    def test_no_inspections(self, tracker):
        report = tracker.daily_report("2026-03-30")
        assert report["inspections"] == 0

    def test_report_with_records(self, tracker, full_record, partial_record):
        tracker.log_inspection(full_record)
        tracker.log_inspection(partial_record)
        report = tracker.daily_report("2026-03-30")
        assert report["inspections"] == 2
        assert report["fully_compliant"] == 1
        assert report["violations"] == 1

    def test_compliance_rate_100_all_compliant(self, tracker, full_record):
        tracker.log_inspection(full_record)
        r2 = InspectionRecord("W-X", "2026-03-30", ["head","foot","eye","hearing","body"], "open_cut")
        tracker.log_inspection(r2)
        report = tracker.daily_report("2026-03-30")
        assert report["compliance_rate_pct"] == pytest.approx(100.0)

    def test_alert_generated_below_threshold(self, tracker, partial_record):
        tracker.log_inspection(partial_record)
        report = tracker.daily_report("2026-03-30")
        assert len(report["alerts"]) > 0

    def test_violator_ids_present(self, tracker, full_record, partial_record):
        tracker.log_inspection(full_record)
        tracker.log_inspection(partial_record)
        report = tracker.daily_report("2026-03-30")
        assert "W-002" in report["violator_ids"]
        assert "W-001" not in report["violator_ids"]


# ---------------------------------------------------------------------------
# worker_history
# ---------------------------------------------------------------------------

class TestWorkerHistory:
    def test_no_records(self, tracker):
        h = tracker.worker_history("UNKNOWN")
        assert h["n_inspections"] == 0

    def test_history_with_records(self, tracker, full_record, partial_record):
        tracker.log_inspection(full_record)
        tracker.log_inspection(partial_record)
        h = tracker.worker_history("W-001")
        assert h["n_inspections"] == 1
        assert h["full_compliance_rate_pct"] == pytest.approx(100.0)

    def test_recurring_missing_detected(self, tracker):
        for i in range(3):
            r = InspectionRecord(f"W-REC", f"2026-03-{15+i:02d}", ["head", "foot"], "open_cut")
            tracker.log_inspection(r)
        h = tracker.worker_history("W-REC")
        assert "eye" in h["recurring_missing_ppe"]


# ---------------------------------------------------------------------------
# zone_summary
# ---------------------------------------------------------------------------

class TestZoneSummary:
    def test_empty_returns_empty(self, tracker):
        assert tracker.zone_summary() == []

    def test_sorted_ascending(self, tracker, full_record, partial_record):
        tracker.log_inspection(full_record)
        tracker.log_inspection(partial_record)
        summary = tracker.zone_summary()
        rates = [z["compliance_rate_pct"] for z in summary]
        assert rates == sorted(rates)

    def test_zone_in_result(self, tracker, full_record):
        tracker.log_inspection(full_record)
        summary = tracker.zone_summary()
        assert any(z["zone"] == "open_cut" for z in summary)

    def test_log_batch(self, tracker, full_record, partial_record):
        tracker.log_batch([full_record, partial_record])
        assert tracker.total_inspections == 2
