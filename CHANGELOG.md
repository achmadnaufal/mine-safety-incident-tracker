# Changelog

## [0.2.0] - 2026-04-16

### Added
- **Comprehensive docstrings** across all public classes and functions in `src/main.py`, `safety_metrics.py`, and `src/analytics/incident_severity_analyzer.py` with usage examples and argument/return documentation.
- **Enhanced input validation** in `SafetyIncidentTracker.validate()`: invalid severity levels, future dates, missing/blank location data, and duplicate `incident_id` values now raise descriptive `ValueError` exceptions.
- **Enhanced input validation** in `SeverityAnalyzer.add_incident()`: invalid severity, negative injured count, non-ISO date format, and duplicate `incident_id` now raise descriptive `ValueError` exceptions.
- **Type hints** added to all public function signatures throughout `src/main.py`, `safety_metrics.py`, and `src/analytics/incident_severity_analyzer.py`.
- **Immutable data patterns**: `SafetyIncidentTracker.preprocess()` returns a new DataFrame without mutating input; `SeverityAnalyzer.incidents` property returns a copy of the internal list; `SafetyMetricsCalculator.analyze()` returns a new dict each call.
- **Additional analysis methods** on `SeverityAnalyzer`: `calculate_weighted_risk_score()`, `get_incidents_by_severity()`, `get_top_locations()`, `summary()`.
- **New test files**:
  - `tests/__init__.py` — marks directory as a Python package.
  - `tests/test_incident_tracker.py` — 40+ tests covering `SafetyIncidentTracker` load, validate, preprocess, analyze, run, and export.
  - `tests/test_incident_severity_analyzer.py` — 35+ tests covering `SeverityAnalyzer` recording, validation, distribution, scoring, and immutability.
  - `tests/test_safety_metrics_extended.py` — 30+ tests covering `SafetyMetricsCalculator` validation, KPI calculations, culture assessment, and reporting structure.
  - `tests/test_trend_and_reporting.py` — 20+ tests for multi-period trend analysis and reporting dict consistency.
- **`demo/sample_data.csv`** — 20 realistic Indonesian coal-mining incident rows covering all severity levels, multiple pit names (Pit-A North, Pit-B South, Coal Processing Plant), incident types (vehicle collision, ground collapse, gas detection, conveyor entanglement, PPE violation, blast exclusion breach), with full metadata columns: `incident_id`, `date`, `time`, `location`, `pit_name`, `incident_type`, `severity`, `description`, `equipment_involved`, `injuries`, `lost_time_days`, `root_cause`, `corrective_action`, `status`.

### Improved
- `SafetyIncidentTracker.run()` now preprocesses before validating so column-name normalisation is applied before required-column checks.
- `SafetyMetricsCalculator` now validates that `mine_name` is not blank in addition to the existing numeric range checks.
- README: added test-running instructions, project structure table, and sample data quick-start section.

---

## [2.10.0] - 2026-04-03

### Added
- **GasMonitoringThresholdChecker** (`src/gas_monitoring_threshold_checker.py`) — Evaluates mine gas sensor readings (CH₄, CO, CO₂, O₂, H₂S, NO₂, SO₂) against 4-level alert thresholds (Advisory/Warning/Action/Evacuation) for underground coal, open-cut coal, and underground metal mines. Includes shift report generator with compliance status, evacuation flags, and ranked recommendations. Aligned with Australian Qld Coal Mining Safety & Health Regulation 2017 and US MSHA 30 CFR Part 75.
- **Unit tests** — 33 tests in `tests/test_gas_monitoring_threshold_checker.py`.

## [2.9.0] - 2026-04-01

### Added
- **Shift Handover Risk Briefing Generator** (`src/analytics/shift_handover_risk_briefing.py`) — structured risk briefings for mine shift handovers per ICMM CCM and ESDM 1827K/2018
  - `HazardItem` dataclass: risk level (LOW/MEDIUM/HIGH/CRITICAL), control status (ACTIVE/PARTIAL/FAILED/PENDING_VERIFICATION), responsible person, critical control name
  - `EquipmentFlag` dataclass: equipment defects with operational restrictions and IMMEDIATE/DEFERRED/MONITOR priority
  - `IsolationRecord` dataclass: area isolations and exclusion zones with IN_PLACE/REMOVED/PARTIAL status
  - `ActionItem` dataclass: open action items with OPEN/IN_PROGRESS/CLOSED lifecycle
  - `ShiftHandoverBriefing.generate()`: full structured briefing dict — critical alerts, failed control list, hazards sorted by risk, equipment flags, active isolations, open actions
  - `render_text()`: human-readable text form for physical handover forms
  - Overall risk level auto-computed as maximum hazard/equipment priority
  - References: ICMM CCM Guide (2019); Kepmen ESDM 1827K/2018 §§42–43; MSHA 30 CFR 56.18002
- **Unit tests** — 19 new tests in `tests/test_shift_handover_risk_briefing.py` (all passing)

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

