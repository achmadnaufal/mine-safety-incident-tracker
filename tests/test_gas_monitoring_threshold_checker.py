"""Tests for GasMonitoringThresholdChecker."""
import pytest
from datetime import datetime
from src.gas_monitoring_threshold_checker import (
    GasMonitoringThresholdChecker,
    GasReading,
    GasType,
    GasAlert,
    AlertLevel,
    MineType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 4, 3, 6, 0, 0)


def make_reading(gas, value, unit="ppm", sensor_id="S01", location="13 Heading"):
    return GasReading(
        sensor_id=sensor_id,
        location=location,
        timestamp=NOW,
        gas=gas,
        value=value,
        unit=unit,
    )


@pytest.fixture
def ug_checker():
    return GasMonitoringThresholdChecker(MineType.UNDERGROUND_COAL)


@pytest.fixture
def oc_checker():
    return GasMonitoringThresholdChecker(MineType.OPEN_CUT_COAL)


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestGasReadingValidation:
    def test_negative_value_raises(self):
        with pytest.raises(ValueError, match=">="):
            GasReading("S1", "loc", NOW, GasType.CH4, -1.0, "% v/v")

    def test_zero_value_valid(self):
        r = GasReading("S1", "loc", NOW, GasType.CH4, 0.0, "% v/v")
        assert r.value == 0.0


# ---------------------------------------------------------------------------
# CH₄ alert levels (underground coal)
# ---------------------------------------------------------------------------

class TestCH4AlertLevels:
    def test_normal(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CH4, 0.1, "% v/v"))
        assert a.alert_level == AlertLevel.NORMAL

    def test_advisory(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CH4, 0.3, "% v/v"))
        assert a.alert_level == AlertLevel.LEVEL_1

    def test_warning(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CH4, 0.6, "% v/v"))
        assert a.alert_level == AlertLevel.LEVEL_2

    def test_action(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CH4, 1.1, "% v/v"))
        assert a.alert_level == AlertLevel.LEVEL_3

    def test_evacuation(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CH4, 1.3, "% v/v"))
        assert a.alert_level == AlertLevel.LEVEL_4


# ---------------------------------------------------------------------------
# CO alert levels
# ---------------------------------------------------------------------------

class TestCOAlertLevels:
    def test_co_normal(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CO, 10))
        assert a.alert_level == AlertLevel.NORMAL

    def test_co_advisory(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CO, 30))
        assert a.alert_level == AlertLevel.LEVEL_1

    def test_co_evacuation(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CO, 450))
        assert a.alert_level == AlertLevel.LEVEL_4


# ---------------------------------------------------------------------------
# O₂ inverse thresholds
# ---------------------------------------------------------------------------

class TestO2InverseThresholds:
    def test_o2_normal(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.O2, 21.0, "% v/v"))
        assert a.alert_level == AlertLevel.NORMAL

    def test_o2_advisory(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.O2, 20.0, "% v/v"))
        assert a.alert_level == AlertLevel.LEVEL_1

    def test_o2_action(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.O2, 18.5, "% v/v"))
        assert a.alert_level == AlertLevel.LEVEL_3

    def test_o2_evacuation(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.O2, 16.0, "% v/v"))
        assert a.alert_level == AlertLevel.LEVEL_4


# ---------------------------------------------------------------------------
# Alert object tests
# ---------------------------------------------------------------------------

class TestAlertObject:
    def test_alert_has_mandatory_action(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CH4, 0.8, "% v/v"))
        assert len(a.mandatory_action) > 0

    def test_evacuation_alert_no_escalation_time(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CH4, 1.5, "% v/v"))
        assert a.escalation_time_min is None

    def test_advisory_has_escalation_time(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CH4, 0.3, "% v/v"))
        assert a.escalation_time_min == 60

    def test_evacuation_action_contains_keyword(self, ug_checker):
        a = ug_checker.check_reading(make_reading(GasType.CH4, 1.5, "% v/v"))
        assert "EVACUATION" in a.mandatory_action or "withdraw" in a.mandatory_action.lower()


# ---------------------------------------------------------------------------
# Batch tests
# ---------------------------------------------------------------------------

class TestBatch:
    def test_batch_length(self, ug_checker):
        readings = [
            make_reading(GasType.CH4, 0.1, "% v/v", "S01"),
            make_reading(GasType.CO, 30, "ppm", "S02"),
            make_reading(GasType.H2S, 8, "ppm", "S03"),
        ]
        alerts = ug_checker.check_readings_batch(readings)
        assert len(alerts) == 3


# ---------------------------------------------------------------------------
# Shift report tests
# ---------------------------------------------------------------------------

class TestShiftReport:
    def test_empty_readings_raises(self, ug_checker):
        with pytest.raises(ValueError, match="empty"):
            ug_checker.generate_shift_report("SITE-01", [],
                                              datetime(2026, 4, 3, 6, 0),
                                              datetime(2026, 4, 3, 18, 0))

    def test_report_compliance_compliant(self, ug_checker):
        readings = [make_reading(GasType.CH4, 0.05, "% v/v")]
        report = ug_checker.generate_shift_report(
            "SITE-01", readings,
            datetime(2026, 4, 3, 6, 0), datetime(2026, 4, 3, 18, 0)
        )
        assert report.compliance_status == "COMPLIANT"

    def test_report_evacuation_required(self, ug_checker):
        readings = [make_reading(GasType.CH4, 2.0, "% v/v")]
        report = ug_checker.generate_shift_report(
            "SITE-01", readings,
            datetime(2026, 4, 3, 6, 0), datetime(2026, 4, 3, 18, 0)
        )
        assert report.evacuation_required is True

    def test_report_recommendations_not_empty(self, ug_checker):
        readings = [make_reading(GasType.CO, 200, "ppm")]
        report = ug_checker.generate_shift_report(
            "SITE-01", readings,
            datetime(2026, 4, 3, 6, 0), datetime(2026, 4, 3, 18, 0)
        )
        assert len(report.recommendations) > 0

    def test_report_total_readings_count(self, ug_checker):
        readings = [
            make_reading(GasType.CH4, 0.1, "% v/v", f"S{i:02d}")
            for i in range(5)
        ]
        report = ug_checker.generate_shift_report(
            "SITE-01", readings,
            datetime(2026, 4, 3, 6, 0), datetime(2026, 4, 3, 18, 0)
        )
        assert report.total_readings == 5

    def test_oc_thresholds_more_permissive(self, ug_checker, oc_checker):
        """Open-cut CH₄ advisory threshold is higher than underground."""
        r = make_reading(GasType.CH4, 0.3, "% v/v")
        alert_ug = ug_checker.check_reading(r)
        alert_oc = oc_checker.check_reading(r)
        # UG advisory at 0.25% → triggers; OC advisory at 0.5% → NORMAL
        # UG should have a higher or equal alert level
        level_priority = {
            AlertLevel.NORMAL: 0, AlertLevel.LEVEL_1: 1, AlertLevel.LEVEL_2: 2,
            AlertLevel.LEVEL_3: 3, AlertLevel.LEVEL_4: 4,
        }
        assert level_priority[alert_ug.alert_level] >= level_priority[alert_oc.alert_level]
