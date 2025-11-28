"""
Unit tests for NearMissTracker.

Tests cover: event recording, validation, risk summary, trending analysis,
area risk matrix, recommendations, and edge cases.
"""
import pytest
from src.analytics.near_miss_tracker import NearMissTracker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_tracker():
    return NearMissTracker(site_name="Test Site")


@pytest.fixture
def populated_tracker():
    t = NearMissTracker(site_name="Pit-A")
    t.record_event("2026-03-01", "Haul Road", "Near Collision",
                   "Truck vs light vehicle", "Critical", shift="Night")
    t.record_event("2026-03-02", "Crusher Area", "Falling Object",
                   "Loose rock from feeder deck", "High", shift="Day")
    t.record_event("2026-03-03", "Pit Floor", "Ground Instability",
                   "Wall slump detected", "Critical", shift="Night")
    t.record_event("2026-03-04", "Workshop", "Electrical Hazard",
                   "Arc flash near terminal", "Medium", shift="Day")
    t.record_event("2026-03-05", "Haul Road", "Near Collision",
                   "Two trucks merging at ramp", "High", shift="Night")
    return t


# ---------------------------------------------------------------------------
# Recording & Validation
# ---------------------------------------------------------------------------


def test_record_event_returns_id(empty_tracker):
    event_id = empty_tracker.record_event(
        "2026-03-10", "Haul Road", "Near Collision", "desc", "High"
    )
    assert event_id == 1


def test_consecutive_ids(empty_tracker):
    id1 = empty_tracker.record_event("2026-03-10", "Haul Road", "Near Collision", "d1", "Low")
    id2 = empty_tracker.record_event("2026-03-11", "Workshop", "Slip/Trip", "d2", "Medium")
    assert id1 == 1
    assert id2 == 2


def test_invalid_severity_raises(empty_tracker):
    with pytest.raises(ValueError, match="Invalid severity"):
        empty_tracker.record_event("2026-03-10", "Haul Road", "Near Collision", "d", "Extreme")


def test_invalid_hazard_type_raises(empty_tracker):
    with pytest.raises(ValueError, match="Invalid hazard_type"):
        empty_tracker.record_event("2026-03-10", "Haul Road", "Explosion", "d", "High")


def test_invalid_date_format_raises(empty_tracker):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        empty_tracker.record_event("23/03/2026", "Haul Road", "Near Collision", "d", "Low")


def test_len(populated_tracker):
    assert len(populated_tracker) == 5


def test_repr(empty_tracker):
    assert "NearMissTracker" in repr(empty_tracker)
    assert "Test Site" in repr(empty_tracker)


# ---------------------------------------------------------------------------
# Risk Summary
# ---------------------------------------------------------------------------


def test_risk_summary_empty(empty_tracker):
    summary = empty_tracker.get_risk_summary()
    assert summary["total_events"] == 0
    assert summary["cumulative_risk_score"] == 0


def test_risk_summary_total(populated_tracker):
    summary = populated_tracker.get_risk_summary()
    assert summary["total_events"] == 5


def test_risk_summary_cumulative_score(populated_tracker):
    # Critical=5, High=3, Critical=5, Medium=2, High=3 → total=18
    summary = populated_tracker.get_risk_summary()
    assert summary["cumulative_risk_score"] == 18


def test_risk_summary_top_hazard(populated_tracker):
    summary = populated_tracker.get_risk_summary()
    assert summary["top_hazard"] == "Near Collision"


def test_risk_summary_top_area(populated_tracker):
    summary = populated_tracker.get_risk_summary()
    assert summary["top_area"] == "Haul Road"


def test_risk_summary_night_shift_pct(populated_tracker):
    # 3 out of 5 events are Night → 60%
    summary = populated_tracker.get_risk_summary()
    assert summary["night_shift_pct"] == 60.0


def test_risk_summary_area_counts(populated_tracker):
    summary = populated_tracker.get_risk_summary()
    assert summary["area_counts"]["Haul Road"] == 2
    assert summary["area_counts"]["Pit Floor"] == 1


# ---------------------------------------------------------------------------
# Trending Hazards
# ---------------------------------------------------------------------------


def test_trending_hazards_empty(empty_tracker):
    assert empty_tracker.get_trending_hazards() == []


def test_trending_hazards_returns_sorted(populated_tracker):
    # Records all have dates in 2026-03 which are within 30 days of "today"
    # We set the dates a bit in the future — function uses today() as reference
    # so we need recent records. Re-create with today's date.
    import datetime
    today = datetime.date.today().isoformat()
    t = NearMissTracker()
    t.record_event(today, "Haul Road", "Near Collision", "d", "High")
    t.record_event(today, "Haul Road", "Near Collision", "d2", "Medium")
    t.record_event(today, "Workshop", "Slip/Trip", "d3", "Low")
    trending = t.get_trending_hazards(window_days=7)
    assert trending[0][0] == "Near Collision"
    assert trending[0][1] == 2


# ---------------------------------------------------------------------------
# Area Risk Matrix
# ---------------------------------------------------------------------------


def test_area_risk_matrix_structure(populated_tracker):
    matrix = populated_tracker.area_risk_matrix()
    assert "Haul Road" in matrix
    assert "Critical" in matrix["Haul Road"]


def test_area_risk_matrix_counts(populated_tracker):
    matrix = populated_tracker.area_risk_matrix()
    assert matrix["Haul Road"]["Critical"] == 1
    assert matrix["Haul Road"]["High"] == 1


def test_area_risk_matrix_empty(empty_tracker):
    assert empty_tracker.area_risk_matrix() == {}


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def test_recommendations_no_data(empty_tracker):
    recs = empty_tracker.recommend_actions()
    assert len(recs) == 1
    assert "No near-miss data" in recs[0]


def test_recommendations_near_collision(populated_tracker):
    recs = populated_tracker.recommend_actions()
    assert any("traffic management" in r.lower() or "Near Collision" in r for r in recs)


def test_recommendations_high_night_shift():
    t = NearMissTracker()
    for i in range(5):
        t.record_event(f"2026-03-{i+1:02d}", "Haul Road", "Near Collision", "d", "High", shift="Night")
    recs = t.recommend_actions()
    assert any("night shift" in r.lower() for r in recs)


def test_recommendations_high_risk_score():
    t = NearMissTracker()
    for i in range(12):
        t.record_event(f"2026-03-{i+1:02d}", "Haul Road", "Near Collision", "d", "Critical")
    recs = t.recommend_actions()
    assert any("stand-down" in r.lower() or "threshold" in r.lower() for r in recs)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_export_records_length(populated_tracker):
    records = populated_tracker.export_records()
    assert len(records) == 5


def test_export_records_fields(populated_tracker):
    record = populated_tracker.export_records()[0]
    assert "id" in record
    assert "date" in record
    assert "hazard_type" in record
    assert "potential_severity" in record
