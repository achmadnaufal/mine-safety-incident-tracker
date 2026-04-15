"""Unit tests for trend analysis and reporting functions.

Tests the ``analyze()`` method of SafetyIncidentTracker and the
``SafetyMetricsCalculator.analyze()`` output used for reporting dashboards.

Covers:
- Trend detection from multi-period datasets
- Period-over-period comparison using SafetyMetricsCalculator
- Severity trend across quarters
- Reporting dict structure consistency
- Edge cases: single record, all same severity, no numeric columns
"""

from __future__ import annotations

import pytest
import pandas as pd

from src.main import SafetyIncidentTracker
from safety_metrics import SafetyMetricsCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_period_df(
    year: int,
    quarter: int,
    low: int = 0,
    medium: int = 0,
    high: int = 0,
    critical: int = 0,
) -> pd.DataFrame:
    """Build a minimal incident DataFrame for a given quarter."""
    rows = []
    month_offset = (quarter - 1) * 3 + 1
    idx = 1
    for sev, count in [("Low", low), ("Medium", medium), ("High", high), ("Critical", critical)]:
        for _ in range(count):
            rows.append(
                {
                    "incident_id": f"{year}Q{quarter}-{idx:03d}",
                    "date": f"{year}-{month_offset:02d}-01",
                    "severity": sev,
                    "location": "Test Location",
                }
            )
            idx += 1
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["incident_id", "date", "severity", "location"]
    )


def _calc_for_period(hours: int, lti: int = 0, med: int = 0,
                     near_miss: int = 0, fatalities: int = 0) -> SafetyMetricsCalculator:
    return SafetyMetricsCalculator(
        mine_name="Trend Mine",
        total_hours_worked=hours,
        fatalities=fatalities,
        lost_time_injuries=lti,
        medical_treatments=med,
        near_misses=near_miss,
    )


# ---------------------------------------------------------------------------
# SafetyIncidentTracker trend tests
# ---------------------------------------------------------------------------


class TestIncidentTrend:
    def test_total_records_matches_row_count(self):
        tracker = SafetyIncidentTracker()
        df = _build_period_df(2026, 1, low=3, medium=2, high=1)
        result = tracker.analyze(df)
        assert result["total_records"] == 6

    def test_severity_distribution_all_high(self):
        tracker = SafetyIncidentTracker()
        df = _build_period_df(2026, 1, high=5)
        result = tracker.analyze(df)
        assert result["severity_distribution"]["High"] == 5
        assert result["severity_distribution"].get("Low", 0) == 0

    def test_severity_distribution_increases_over_quarters(self):
        tracker = SafetyIncidentTracker()
        q1 = _build_period_df(2026, 1, high=2)
        q2 = _build_period_df(2026, 2, high=5)
        r1 = tracker.analyze(q1)
        r2 = tracker.analyze(q2)
        assert r2["severity_distribution"]["High"] > r1["severity_distribution"]["High"]

    def test_empty_after_preprocessing_handled(self):
        tracker = SafetyIncidentTracker()
        # Completely empty DF (no rows, some columns)
        import numpy as np
        df = pd.DataFrame([{"incident_id": np.nan, "date": np.nan, "severity": np.nan,
                            "location": np.nan}])
        # After dropna(how="all"), this row is removed → result has 0 records
        result = tracker.analyze(df)
        assert result["total_records"] == 0

    def test_mixed_severity_distribution_sum(self):
        tracker = SafetyIncidentTracker()
        df = _build_period_df(2026, 2, low=1, medium=2, high=3, critical=1)
        result = tracker.analyze(df)
        total = sum(result["severity_distribution"].values())
        assert total == result["total_records"] == 7

    def test_analyze_does_not_mutate_input(self):
        tracker = SafetyIncidentTracker()
        df = _build_period_df(2026, 1, high=3)
        original_cols = list(df.columns)
        tracker.analyze(df)
        assert list(df.columns) == original_cols


# ---------------------------------------------------------------------------
# SafetyMetricsCalculator period comparison tests
# ---------------------------------------------------------------------------


class TestMetricsTrend:
    def test_improving_trifr_across_periods(self):
        q1 = _calc_for_period(300_000, lti=5, med=8)
        q2 = _calc_for_period(300_000, lti=2, med=3)
        assert q2.calculate_trifr() < q1.calculate_trifr()

    def test_declining_ltifr_across_periods(self):
        q1 = _calc_for_period(300_000, lti=6)
        q2 = _calc_for_period(300_000, lti=2)
        assert q2.calculate_ltifr() < q1.calculate_ltifr()

    def test_near_miss_ratio_improves_with_reporting(self):
        # Same LTI, more near-misses reported → proactive culture
        c_low_reporting = _calc_for_period(500_000, lti=2, near_miss=4)
        c_high_reporting = _calc_for_period(500_000, lti=2, near_miss=40)
        assert c_high_reporting.calculate_near_miss_ratio() > c_low_reporting.calculate_near_miss_ratio()

    def test_culture_improves_with_better_metrics(self):
        poor_mine = _calc_for_period(100_000, fatalities=2, lti=10, med=8)
        excellent_mine = _calc_for_period(1_000_000, lti=2, near_miss=50)
        assert poor_mine.assess_safety_culture() == "poor"
        assert excellent_mine.assess_safety_culture() == "excellent"

    def test_multi_period_report_keys_consistent(self):
        required_keys = {
            "mine_name", "total_hours_worked", "trifr", "ltifr",
            "fatality_rate_per_1m", "near_miss_ratio", "safety_culture",
        }
        for lti in [1, 3, 5, 8]:
            calc = _calc_for_period(500_000, lti=lti, near_miss=lti * 5)
            report = calc.analyze()
            assert required_keys.issubset(report.keys())

    def test_analyze_produces_distinct_objects(self):
        calc = _calc_for_period(500_000, lti=3)
        r1 = calc.analyze()
        r2 = calc.analyze()
        assert r1 is not r2

    def test_zero_incident_period_reports_zero_rates(self):
        calc = _calc_for_period(400_000)
        report = calc.analyze()
        assert report["trifr"] == 0.0
        assert report["ltifr"] == 0.0
        assert report["fatality_rate_per_1m"] == 0.0


# ---------------------------------------------------------------------------
# Reporting dict structure tests
# ---------------------------------------------------------------------------


class TestReportingStructure:
    def test_to_dataframe_covers_all_keys(self):
        tracker = SafetyIncidentTracker()
        df = _build_period_df(2026, 1, low=1, high=2)
        result = tracker.analyze(df)
        export_df = tracker.to_dataframe(result)
        # Every top-level key should appear at least once in metric column
        for key in result:
            match = export_df["metric"].str.startswith(key)
            assert match.any(), f"Key '{key}' not found in exported DataFrame"

    def test_to_dataframe_no_nested_dict_values(self):
        tracker = SafetyIncidentTracker()
        df = _build_period_df(2026, 1, medium=3)
        result = tracker.analyze(df)
        export_df = tracker.to_dataframe(result)
        for val in export_df["value"]:
            assert not isinstance(val, dict)

    def test_missing_pct_sums_to_valid_range(self):
        tracker = SafetyIncidentTracker()
        df = _build_period_df(2026, 1, high=4)
        result = tracker.analyze(df)
        for col, pct in result["missing_pct"].items():
            assert 0.0 <= pct <= 100.0, f"missing_pct[{col}] = {pct} out of range"
