# Mine Safety Incident Tracker

Mining safety incident tracking, classification, and trend analysis system

## Features
- Data ingestion from CSV/Excel input files
- Automated analysis and KPI calculation
- Summary statistics and trend reporting
- Sample data generator for testing and development

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from src.main import SafetyIncidentTracker

analyzer = SafetyIncidentTracker()
df = analyzer.load_data("data/sample.csv")
result = analyzer.analyze(df)
print(result)
```

## Data Format

Expected CSV columns: `incident_id, date, pit, type, severity, lost_time_days, root_cause, corrective_action`

## Project Structure

```
mine-safety-incident-tracker/
├── src/
│   ├── main.py          # Core analysis logic
│   └── data_generator.py # Sample data generator
├── data/                # Data directory (gitignored for real data)
├── examples/            # Usage examples
├── requirements.txt
└── README.md
```

## License

MIT License — free to use, modify, and distribute.

## Incident Severity Analyzer

Track and analyze safety incident patterns:

```python
from src.analytics.incident_severity_analyzer import SeverityAnalyzer

analyzer = SeverityAnalyzer()
analyzer.add_incident('2026-03-01', 'High', 'Equipment failure', injured=2)
distribution = analyzer.get_severity_distribution()
print(f'Critical incidents: {distribution["Critical"]}')
```

## Near Miss Tracking (New in v2.6.0)

Near misses are unplanned events that *could have* caused harm. Tracking them is the cornerstone of proactive safety culture.

```python
from src.analytics.near_miss_tracker import NearMissTracker

tracker = NearMissTracker(site_name="Pit-A North")

tracker.record_event(
    date="2026-03-23",
    area="Haul Road",
    hazard_type="Near Collision",
    description="Dump truck overtook light vehicle at blind corner near Pit-A junction",
    potential_severity="Critical",
    reported_by="EMP-0421",
    corrective_action="Speed restriction enforced; additional signage installed",
    shift="Day",
)

# Get risk summary
summary = tracker.get_risk_summary()
print(f"Total events: {summary['total_events']}")
print(f"Cumulative risk score: {summary['cumulative_risk_score']}")
print(f"Top hazard: {summary['top_hazard']}")

# Corrective action recommendations
for rec in tracker.recommend_actions():
    print(rec)

# Area × severity risk matrix
matrix = tracker.area_risk_matrix()
```

### Hazard Types
`Near Collision`, `Falling Object`, `Slip/Trip`, `Equipment Malfunction`,
`Electrical Hazard`, `Ground Instability`, `Dust/Gas Exposure`, `Blast Proximity`,
`Unsecured Load`, `Other`

### Severity Weights
| Severity | Weight |
|----------|--------|
| Low      | 1      |
| Medium   | 2      |
| High     | 3      |
| Critical | 5      |

See `data/sample_incidents.csv` for 20 realistic near-miss examples from an open-cut coal operation.

