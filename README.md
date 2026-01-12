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
