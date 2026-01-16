# Changelog

## [2.8.0] - 2026-03-30

### Added
- **PPE Compliance Tracker** (`src/analytics/ppe_compliance_tracker.py`) — zone-specific PPE compliance tracking per Indonesian ESDM and ICMM standards
  - 5 mine zones: open_cut, underground, wash_plant, workshop, control_room with mandatory PPE requirements
  - 7 PPE categories: head, eye, hearing, foot, body, hand, respiratory (with severity weights)
  - `InspectionRecord` dataclass with full input validation (zone, ppe item, shift)
  - `ComplianceScore`: full/partial compliance, missing PPE list, severity-weighted score (0–100), risk level (OK/LOW/MODERATE/HIGH/CRITICAL)
  - `log_inspection()` / `log_batch()`: record management
  - `daily_report()`: compliance rate, violations, alerts when below threshold, most-missed PPE
  - `worker_history()`: per-worker compliance trend, recurring missing PPE detection
  - `zone_summary()`: all-zone compliance ranking sorted worst-first
- **Unit tests** — 37 new tests in `tests/test_ppe_compliance_tracker.py`

### References
- Kepmen ESDM 1827K/30/MEM/2018 Indonesian Mine Safety Technical Guidelines.
- ICMM (2019) Health and Safety: Critical Control Management Guide.
- ILO (2022) Safety and Health in Mining Guidelines, 2nd ed.

## [2.7.0] - 2026-03-26

### Added
- **SafetyLeadingIndicatorTracker** (`src/analytics/safety_leading_indicator_tracker.py`) — ICMM-aligned proactive safety metrics
  - 7 leading indicators: safety observations, near-miss reporting, critical risk verifications, training compliance, pre-shift inspections, toolbox talks, action close-out
  - Weighted Safety Health Index (SHI): 0–100 composite score
  - RAG status per indicator and overall: GREEN (≥80) / AMBER (60–79) / RED (<60)
  - Critical risk verifications weighted most heavily (25%) — highest predictor of incidents
  - Trend tracking: SHI delta vs prior period
  - Priority action generation: one-line corrective action per RED/AMBER indicator
  - `score_portfolio()`: multi-crew scoring sorted by SHI descending
  - `site_summary()`: aggregate RAG distribution, avg SHI, most common RED indicator
  - Custom weight override with validation
- Unit tests: 13 new tests in `tests/test_safety_leading_indicator_tracker.py`

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

