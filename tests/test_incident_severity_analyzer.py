"""Unit tests for SeverityAnalyzer (src/analytics/incident_severity_analyzer.py).

Covers:
- Valid incident recording
- Input validation: invalid severity, negative injured count, bad date format,
  duplicate incident IDs
- Severity distribution accuracy
- Weighted risk score computation
- Total injured aggregation
- get_incidents_by_severity filtering
- get_top_locations ranking
- summary() output structure
- Immutability: incidents property returns a copy
"""

from __future__ import annotations

import pytest
from src.analytics.incident_severity_analyzer import SeverityAnalyzer, SEVERITY_WEIGHTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_analyzer():
    return SeverityAnalyzer()


@pytest.fixture
def populated_analyzer():
    a = SeverityAnalyzer()
    a.add_incident("2026-01-10", "High", "Highwall collapse", injured=2,
                   location="Pit-A Bench 3", incident_id="INC-001")
    a.add_incident("2026-01-15", "Medium", "Slip on wet steps", injured=0,
                   location="Workshop", incident_id="INC-002")
    a.add_incident("2026-02-01", "Critical", "Equipment rollover", injured=1,
                   location="Overburden Dump", incident_id="INC-003")
    a.add_incident("2026-02-10", "Low", "Minor abrasion", injured=1,
                   location="Workshop", incident_id="INC-004")
    a.add_incident("2026-03-05", "High", "Conveyor entanglement", injured=1,
                   location="Processing Plant", incident_id="INC-005")
    return a


# ---------------------------------------------------------------------------
# add_incident tests
# ---------------------------------------------------------------------------


class TestAddIncident:
    def test_adds_one_incident(self, empty_analyzer):
        idx = empty_analyzer.add_incident("2026-01-01", "Low", "Test incident")
        assert idx == 1
        assert len(empty_analyzer.incidents) == 1

    def test_returns_sequential_index(self, empty_analyzer):
        idx1 = empty_analyzer.add_incident("2026-01-01", "Low", "First")
        idx2 = empty_analyzer.add_incident("2026-01-02", "Medium", "Second")
        assert idx1 == 1
        assert idx2 == 2

    def test_all_severity_levels_accepted(self, empty_analyzer):
        for i, sev in enumerate(SEVERITY_WEIGHTS):
            empty_analyzer.add_incident(f"2026-0{i+1}-01", sev, f"Incident {i}",
                                        incident_id=f"AUTO-{i}")
        assert len(empty_analyzer.incidents) == 4

    def test_invalid_severity_raises(self, empty_analyzer):
        with pytest.raises(ValueError, match="Invalid severity"):
            empty_analyzer.add_incident("2026-01-01", "Catastrophic", "desc")

    def test_negative_injured_raises(self, empty_analyzer):
        with pytest.raises(ValueError, match="Injured count cannot be negative"):
            empty_analyzer.add_incident("2026-01-01", "Low", "desc", injured=-1)

    def test_invalid_date_format_raises(self, empty_analyzer):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            empty_analyzer.add_incident("01/01/2026", "Low", "desc")

    def test_duplicate_incident_id_raises(self, empty_analyzer):
        empty_analyzer.add_incident("2026-01-01", "Low", "First", incident_id="ID-001")
        with pytest.raises(ValueError, match="already exists"):
            empty_analyzer.add_incident("2026-01-02", "Medium", "Second", incident_id="ID-001")

    def test_auto_generated_id_when_not_provided(self, empty_analyzer):
        empty_analyzer.add_incident("2026-01-01", "Low", "desc")
        assert empty_analyzer.incidents[0]["incident_id"] == "1"

    def test_location_stored_stripped(self, empty_analyzer):
        empty_analyzer.add_incident("2026-01-01", "Low", "desc",
                                    location="  Haul Road  ")
        assert empty_analyzer.incidents[0]["location"] == "Haul Road"

    def test_severity_weight_stored(self, empty_analyzer):
        empty_analyzer.add_incident("2026-01-01", "Critical", "desc")
        assert empty_analyzer.incidents[0]["severity_weight"] == SEVERITY_WEIGHTS["Critical"]


# ---------------------------------------------------------------------------
# Immutability tests
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_incidents_property_returns_copy(self, populated_analyzer):
        copy = populated_analyzer.incidents
        copy.clear()
        assert len(populated_analyzer.incidents) == 5

    def test_modifying_returned_incident_dict_does_not_affect_state(
        self, populated_analyzer
    ):
        inc = populated_analyzer.incidents[0]
        inc["severity"] = "Low"
        # Original should still be "High"
        assert populated_analyzer.incidents[0]["severity"] == "High"


# ---------------------------------------------------------------------------
# get_severity_distribution tests
# ---------------------------------------------------------------------------


class TestGetSeverityDistribution:
    def test_all_levels_present_in_output(self, empty_analyzer):
        dist = empty_analyzer.get_severity_distribution()
        assert set(dist.keys()) == set(SEVERITY_WEIGHTS.keys())

    def test_empty_analyzer_all_zeros(self, empty_analyzer):
        dist = empty_analyzer.get_severity_distribution()
        assert all(v == 0 for v in dist.values())

    def test_counts_match_added_incidents(self, populated_analyzer):
        dist = populated_analyzer.get_severity_distribution()
        assert dist["High"] == 2
        assert dist["Medium"] == 1
        assert dist["Critical"] == 1
        assert dist["Low"] == 1

    def test_total_equals_incident_count(self, populated_analyzer):
        dist = populated_analyzer.get_severity_distribution()
        assert sum(dist.values()) == len(populated_analyzer.incidents)


# ---------------------------------------------------------------------------
# calculate_weighted_risk_score tests
# ---------------------------------------------------------------------------


class TestWeightedRiskScore:
    def test_empty_returns_zero(self, empty_analyzer):
        assert empty_analyzer.calculate_weighted_risk_score() == 0

    def test_single_critical_returns_weight_5(self, empty_analyzer):
        empty_analyzer.add_incident("2026-01-01", "Critical", "desc")
        assert empty_analyzer.calculate_weighted_risk_score() == 5

    def test_mixed_severity_score(self, populated_analyzer):
        # High(3) + Medium(2) + Critical(5) + Low(1) + High(3) = 14
        assert populated_analyzer.calculate_weighted_risk_score() == 14

    def test_score_increases_with_new_incidents(self, empty_analyzer):
        empty_analyzer.add_incident("2026-01-01", "Low", "desc")
        score1 = empty_analyzer.calculate_weighted_risk_score()
        empty_analyzer.add_incident("2026-01-02", "High", "desc", incident_id="X-2")
        score2 = empty_analyzer.calculate_weighted_risk_score()
        assert score2 > score1


# ---------------------------------------------------------------------------
# get_total_injured tests
# ---------------------------------------------------------------------------


class TestGetTotalInjured:
    def test_empty_returns_zero(self, empty_analyzer):
        assert empty_analyzer.get_total_injured() == 0

    def test_correct_sum(self, populated_analyzer):
        # 2 + 0 + 1 + 1 + 1 = 5
        assert populated_analyzer.get_total_injured() == 5

    def test_zero_injured_contributes_nothing(self, empty_analyzer):
        empty_analyzer.add_incident("2026-01-01", "High", "desc", injured=0)
        assert empty_analyzer.get_total_injured() == 0


# ---------------------------------------------------------------------------
# get_incidents_by_severity tests
# ---------------------------------------------------------------------------


class TestGetIncidentsBySeverity:
    def test_returns_matching_incidents(self, populated_analyzer):
        high = populated_analyzer.get_incidents_by_severity("High")
        assert len(high) == 2
        assert all(inc["severity"] == "High" for inc in high)

    def test_empty_result_for_missing_severity(self, populated_analyzer):
        result = populated_analyzer.get_incidents_by_severity("Low")
        assert len(result) == 1

    def test_invalid_severity_returns_empty_list(self, populated_analyzer):
        result = populated_analyzer.get_incidents_by_severity("Unknown")
        assert result == []


# ---------------------------------------------------------------------------
# get_top_locations tests
# ---------------------------------------------------------------------------


class TestGetTopLocations:
    def test_returns_sorted_by_count(self, populated_analyzer):
        # Workshop appears twice, others once
        top = populated_analyzer.get_top_locations()
        assert top[0][0] == "Workshop"
        assert top[0][1] == 2

    def test_empty_returns_empty(self, empty_analyzer):
        assert empty_analyzer.get_top_locations() == []

    def test_top_n_respected(self, populated_analyzer):
        top = populated_analyzer.get_top_locations(top_n=2)
        assert len(top) <= 2


# ---------------------------------------------------------------------------
# summary tests
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_keys_present(self, populated_analyzer):
        s = populated_analyzer.summary()
        assert "total_incidents" in s
        assert "total_injured" in s
        assert "weighted_risk_score" in s
        assert "severity_distribution" in s
        assert "top_locations" in s

    def test_summary_values_consistent(self, populated_analyzer):
        s = populated_analyzer.summary()
        assert s["total_incidents"] == len(populated_analyzer.incidents)
        assert s["total_injured"] == populated_analyzer.get_total_injured()
        assert s["weighted_risk_score"] == populated_analyzer.calculate_weighted_risk_score()
