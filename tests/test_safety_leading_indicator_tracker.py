"""Unit tests for SafetyLeadingIndicatorTracker."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "analytics"))

from analytics.safety_leading_indicator_tracker import (
    SafetyLeadingIndicatorTracker,
    LeadingIndicatorRecord,
    RAGStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_record(
    crew_id="CREW_A",
    obs_done=45, obs_target=50,
    nm_done=8, nm_target=6,
    crv_done=28, crv_target=30,
    train_done=58, workforce=62,
    psi_done=140, psi_req=150,
    tt_done=14, tt_req=15,
    action_done=9, action_due=12,
) -> LeadingIndicatorRecord:
    return LeadingIndicatorRecord(
        crew_id=crew_id,
        period="W12-2026",
        site="Berau Mine",
        safety_obs_completed=obs_done, safety_obs_target=obs_target,
        near_miss_reported=nm_done, near_miss_target=nm_target,
        critical_risk_verifications_completed=crv_done, critical_risk_verifications_target=crv_target,
        training_current_count=train_done, total_workforce=workforce,
        pre_shift_inspections_completed=psi_done, pre_shift_inspections_required=psi_req,
        toolbox_talks_delivered=tt_done, toolbox_talks_required=tt_req,
        actions_closed_on_time=action_done, total_actions_due=action_due,
    )


# ---------------------------------------------------------------------------
# LeadingIndicatorRecord tests
# ---------------------------------------------------------------------------

class TestLeadingIndicatorRecord:
    def test_safety_obs_rate(self):
        r = make_record(obs_done=45, obs_target=50)
        assert abs(r.safety_obs_rate_pct - 90.0) < 0.01

    def test_near_miss_rate_capped_at_100(self):
        r = make_record(nm_done=10, nm_target=5)
        assert r.near_miss_rate_pct == 100.0

    def test_training_compliance(self):
        r = make_record(train_done=50, workforce=100)
        assert abs(r.training_compliance_pct - 50.0) < 0.01

    def test_action_closeout_zero_due(self):
        r = make_record(action_done=0, action_due=0)
        assert r.action_closeout_rate_pct == 100.0

    def test_zero_target_raises(self):
        with pytest.raises(ValueError):
            make_record(obs_target=0)

    def test_training_exceeds_workforce_raises(self):
        with pytest.raises(ValueError):
            make_record(train_done=100, workforce=50)


# ---------------------------------------------------------------------------
# SafetyLeadingIndicatorTracker tests
# ---------------------------------------------------------------------------

class TestTracker:
    def setup_method(self):
        self.tracker = SafetyLeadingIndicatorTracker()

    def test_score_returns_shi(self):
        r = make_record()
        score = self.tracker.score(r)
        assert 0 <= score.composite_shi <= 100

    def test_high_performance_green(self):
        r = make_record(obs_done=50, nm_done=8, crv_done=30, train_done=62, psi_done=150, tt_done=15, action_done=12)
        score = self.tracker.score(r)
        assert score.overall_rag == RAGStatus.GREEN

    def test_low_performance_red(self):
        r = make_record(obs_done=5, nm_done=1, crv_done=5, train_done=20, psi_done=30, tt_done=3, action_done=1)
        score = self.tracker.score(r)
        assert score.overall_rag == RAGStatus.RED

    def test_red_indicators_populated(self):
        r = make_record(crv_done=5, crv_target=30)  # critical risk verifications at 17%
        score = self.tracker.score(r)
        assert "critical_risk_verifications" in score.red_indicators

    def test_all_indicators_scored(self):
        r = make_record()
        score = self.tracker.score(r)
        expected = {"safety_observations", "near_miss_reporting", "critical_risk_verifications",
                    "training_compliance", "pre_shift_inspections", "toolbox_talks", "action_closeout"}
        assert set(score.indicator_scores.keys()) == expected

    def test_trend_calculated(self):
        r = make_record()
        score = self.tracker.score(r, prior_shi=75.0)
        assert score.trend_vs_last is not None

    def test_trend_none_without_prior(self):
        r = make_record()
        score = self.tracker.score(r)
        assert score.trend_vs_last is None

    def test_portfolio_score_sorted(self):
        records = [
            make_record(f"C{i}", obs_done=10*i, crv_done=3*i, crv_target=30) for i in range(1, 4)
        ]
        scores = self.tracker.score_portfolio(records)
        shi_values = [s.composite_shi for s in scores]
        assert shi_values == sorted(shi_values, reverse=True)

    def test_portfolio_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self.tracker.score_portfolio([])

    def test_site_summary(self):
        records = [make_record(f"C{i}") for i in range(3)]
        scores = self.tracker.score_portfolio(records)
        summary = self.tracker.site_summary(scores)
        assert summary["total_crews"] == 3
        assert "avg_shi" in summary

    def test_invalid_record_type_raises(self):
        with pytest.raises(TypeError):
            self.tracker.score({"crew_id": "bad"})

    def test_invalid_weights_raise(self):
        with pytest.raises(ValueError, match="sum to 1.0"):
            SafetyLeadingIndicatorTracker(weights={"a": 0.3, "b": 0.4})
