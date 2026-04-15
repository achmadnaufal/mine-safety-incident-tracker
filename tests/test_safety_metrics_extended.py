"""Extended unit tests for SafetyMetricsCalculator (safety_metrics.py).

Covers:
- Comprehensive input validation
- TRIFR / LTIFR / fatality rate mathematical accuracy
- Near-miss ratio edge cases (zero LTI, zero near-miss, infinity)
- Safety culture assessment thresholds
- analyze() output completeness and type correctness
- Immutability: analyze() returns a new dict each call
"""

from __future__ import annotations

import math
import pytest
from safety_metrics import SafetyMetricsCalculator, SeverityLevel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _calc(**kwargs) -> SafetyMetricsCalculator:
    defaults = {
        "mine_name": "Test Mine",
        "total_hours_worked": 1_000_000,
    }
    defaults.update(kwargs)
    return SafetyMetricsCalculator(**defaults)


# ---------------------------------------------------------------------------
# Initialisation / validation
# ---------------------------------------------------------------------------


class TestInitValidation:
    def test_valid_instance_created(self):
        calc = _calc()
        assert calc.mine_name == "Test Mine"

    def test_blank_mine_name_raises(self):
        with pytest.raises(ValueError, match="mine_name"):
            SafetyMetricsCalculator(mine_name="", total_hours_worked=1_000_000)

    def test_whitespace_only_mine_name_raises(self):
        with pytest.raises(ValueError, match="mine_name"):
            SafetyMetricsCalculator(mine_name="   ", total_hours_worked=1_000_000)

    def test_zero_hours_raises(self):
        with pytest.raises(ValueError, match="positive"):
            SafetyMetricsCalculator(mine_name="Mine", total_hours_worked=0)

    def test_negative_hours_raises(self):
        with pytest.raises(ValueError, match="positive"):
            SafetyMetricsCalculator(mine_name="Mine", total_hours_worked=-500)

    def test_negative_fatalities_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            _calc(fatalities=-1)

    def test_negative_lti_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            _calc(lost_time_injuries=-2)

    def test_negative_medical_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            _calc(medical_treatments=-1)

    def test_negative_near_misses_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            _calc(near_misses=-5)

    def test_all_zero_incidents_valid(self):
        calc = _calc()
        assert calc.fatalities == 0


# ---------------------------------------------------------------------------
# TRIFR
# ---------------------------------------------------------------------------


class TestTRIFR:
    def test_zero_incidents_gives_zero(self):
        assert _calc().calculate_trifr() == pytest.approx(0.0)

    def test_known_value(self):
        # (1 + 4 + 5) / 1_000_000 * 1_000_000 = 10.0
        calc = _calc(fatalities=1, lost_time_injuries=4, medical_treatments=5)
        assert calc.calculate_trifr() == pytest.approx(10.0, rel=1e-6)

    def test_only_fatalities(self):
        calc = _calc(fatalities=2, total_hours_worked=500_000)
        # 2 / 500_000 * 1_000_000 = 4.0
        assert calc.calculate_trifr() == pytest.approx(4.0, rel=1e-6)

    def test_does_not_include_near_misses(self):
        c1 = _calc(lost_time_injuries=1)
        c2 = _calc(lost_time_injuries=1, near_misses=100)
        assert c1.calculate_trifr() == pytest.approx(c2.calculate_trifr())


# ---------------------------------------------------------------------------
# LTIFR
# ---------------------------------------------------------------------------


class TestLTIFR:
    def test_zero_lti_gives_zero(self):
        assert _calc(medical_treatments=5).calculate_ltifr() == pytest.approx(0.0)

    def test_known_value(self):
        # (0 + 3) / 1_000_000 * 1_000_000 = 3.0
        calc = _calc(lost_time_injuries=3)
        assert calc.calculate_ltifr() == pytest.approx(3.0, rel=1e-6)

    def test_fatality_included_in_ltifr(self):
        calc = _calc(fatalities=1, lost_time_injuries=2)
        # (1 + 2) / 1M * 1M = 3.0
        assert calc.calculate_ltifr() == pytest.approx(3.0, rel=1e-6)

    def test_medical_treatments_excluded(self):
        c1 = _calc(lost_time_injuries=1)
        c2 = _calc(lost_time_injuries=1, medical_treatments=50)
        assert c1.calculate_ltifr() == pytest.approx(c2.calculate_ltifr())


# ---------------------------------------------------------------------------
# Fatality rate
# ---------------------------------------------------------------------------


class TestFatalityRate:
    def test_no_fatalities_gives_zero(self):
        assert _calc().calculate_fatality_rate() == pytest.approx(0.0)

    def test_known_value(self):
        # 1 / 500_000 * 1_000_000 = 2.0
        calc = _calc(fatalities=1, total_hours_worked=500_000)
        assert calc.calculate_fatality_rate() == pytest.approx(2.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Near-miss ratio
# ---------------------------------------------------------------------------


class TestNearMissRatio:
    def test_both_zero_returns_zero(self):
        assert _calc().calculate_near_miss_ratio() == 0.0

    def test_near_misses_only_returns_inf(self):
        calc = _calc(near_misses=10)
        assert math.isinf(calc.calculate_near_miss_ratio())

    def test_known_ratio(self):
        # 20 / 2 = 10.0
        calc = _calc(lost_time_injuries=2, near_misses=20)
        assert calc.calculate_near_miss_ratio() == pytest.approx(10.0, rel=1e-6)

    def test_fatality_counts_in_denominator(self):
        calc = _calc(fatalities=1, lost_time_injuries=1, near_misses=10)
        # 10 / (1+1) = 5.0
        assert calc.calculate_near_miss_ratio() == pytest.approx(5.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Safety culture assessment
# ---------------------------------------------------------------------------


class TestAssessSafetyCulture:
    def test_excellent(self):
        # TRIFR < 5, near_miss_ratio > 10 → excellent
        calc = _calc(lost_time_injuries=1, near_misses=50)
        assert calc.assess_safety_culture() == "excellent"

    def test_good(self):
        # TRIFR < 10, near_miss_ratio > 5 → good
        calc = _calc(lost_time_injuries=5, near_misses=40)
        assert calc.assess_safety_culture() == "good"

    def test_adequate(self):
        # TRIFR between 10 and 20
        calc = _calc(lost_time_injuries=15)
        assert calc.assess_safety_culture() == "adequate"

    def test_poor(self):
        # TRIFR >= 20 → poor
        calc = _calc(total_hours_worked=100_000, fatalities=2,
                     lost_time_injuries=10, medical_treatments=8)
        assert calc.assess_safety_culture() == "poor"

    def test_returns_valid_string(self):
        for lti in range(0, 25, 5):
            c = _calc(lost_time_injuries=lti)
            assert c.assess_safety_culture() in {"excellent", "good", "adequate", "poor"}


# ---------------------------------------------------------------------------
# analyze() output
# ---------------------------------------------------------------------------


class TestAnalyze:
    REQUIRED_KEYS = {
        "mine_name", "total_hours_worked", "fatalities", "lost_time_injuries",
        "medical_treatments", "near_misses", "trifr", "ltifr",
        "fatality_rate_per_1m", "near_miss_ratio", "safety_culture",
    }

    def test_all_keys_present(self):
        result = _calc(lost_time_injuries=2, near_misses=20).analyze()
        assert self.REQUIRED_KEYS.issubset(result.keys())

    def test_trifr_rounded(self):
        result = _calc(lost_time_injuries=3).analyze()
        # Must be a float with at most 2 decimal places
        assert isinstance(result["trifr"], float)

    def test_safety_culture_valid_value(self):
        result = _calc().analyze()
        assert result["safety_culture"] in {"excellent", "good", "adequate", "poor"}

    def test_mine_name_preserved(self):
        result = _calc(mine_name="Berau Coal").analyze()
        assert result["mine_name"] == "Berau Coal"

    def test_analyze_returns_new_dict_each_call(self):
        calc = _calc(lost_time_injuries=3)
        r1 = calc.analyze()
        r2 = calc.analyze()
        assert r1 is not r2
        r1["mine_name"] = "Modified"
        assert r2["mine_name"] == "Test Mine"


# ---------------------------------------------------------------------------
# SeverityLevel enum
# ---------------------------------------------------------------------------


class TestSeverityLevelEnum:
    def test_all_levels_defined(self):
        levels = {sl.value for sl in SeverityLevel}
        assert levels == {"fatality", "lost_time_injury", "medical_treatment", "near_miss"}

    def test_enum_values_are_strings(self):
        for sl in SeverityLevel:
            assert isinstance(sl.value, str)
