# Changelog

## [2.6.0] - 2026-03-23

### Added
- `NearMissTracker` class in `src/analytics/near_miss_tracker.py`
  - Near-miss event recording with hazard type, area, severity, and shift
  - Cumulative risk score (severity-weighted)
  - `get_risk_summary()` — counts by area, hazard, severity + night-shift %
  - `get_trending_hazards(window_days)` — trending hazards in rolling window
  - `area_risk_matrix()` — cross-tab of area × severity counts
  - `recommend_actions()` — rule-based corrective action recommendations
  - Full input validation with descriptive error messages
- `data/sample_incidents.csv` — 20 realistic near-miss records from open-cut coal operations
- 25 new unit tests in `tests/test_near_miss_tracker.py`

### Improved
- README: added Near Miss Tracking section with code examples and severity table

## [2.5.0] - 2026-03-03

### Added
- Incident Severity Analyzer for pattern analysis
- Classification into Low/Medium/High/Critical categories
- Injury tracking and aggregation
- Severity distribution analysis
- Unit tests for severity analyzer (4 test cases)
- Sample incident log data
- Comprehensive input validation

### Improved
- Better incident tracking structure
- Human-readable severity levels

