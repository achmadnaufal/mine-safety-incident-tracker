# 🪖 Mine Safety Incident Tracker

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square&logo=python" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License">
  <img src="https://img.shields.io/badge/domain-Mining%20Safety-c0392b?style=flat-square" alt="Mining Safety">
  <img src="https://img.shields.io/badge/framework-ICMM%20Safety-orange?style=flat-square" alt="ICMM">
  <img src="https://img.shields.io/badge/tests-passing-brightgreen?style=flat-square" alt="Tests">
</p>

> A mining safety incident tracking, classification, and trend analysis system for open-cut coal operations. Covers incident severity scoring, near-miss tracking, PPE compliance monitoring, root cause analysis, and proactive corrective action recommendations. Aligned with ICMM Safety Performance Framework and Queensland mine safety regulations.

---

## 🎯 Features

- **Incident Classification** — Automatic severity scoring (Low / Medium / High / Critical) with weighted risk index
- **Near-Miss Tracking** — Proactive near-miss logging with hazard type taxonomy and corrective action engine
- **PPE Compliance Monitor** — Zone-specific PPE compliance rates with daily reports and threshold alerts
- **Root Cause Analysis** — Structured RCA categorization with corrective action tracking
- **LTI Frequency Rate** — Automated LTIFR calculation vs industry benchmarks
- **Trend Analysis** — QoQ and YoY incident trends with visual summaries
- **Corrective Action Engine** — Auto-generated prioritized recommendations from incident patterns
- **Sample Data Generator** — Realistic synthetic incident data for 50+ open-cut coal scenarios

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/achmadnaufal/mine-safety-incident-tracker.git
cd mine-safety-incident-tracker
pip install -r requirements.txt
```

### Basic Usage

```python
from src.main import SafetyIncidentTracker

tracker = SafetyIncidentTracker()
df = tracker.load_data("data/sample_incidents.csv")
report = tracker.analyze(df)

print(f"Total Incidents      : {report['total_incidents']}")
print(f"Lost-Time Injuries   : {report['lti_count']}")
print(f"LTIFR                : {report['ltifr']:.2f}")
print(f"Top Hazard Location  : {report['top_location']}")
```

### Near-Miss Tracking

```python
from src.analytics.near_miss_tracker import NearMissTracker

tracker = NearMissTracker(site_name="Pit-A North")

tracker.record_event(
    date="2026-03-30",
    area="Haul Road",
    hazard_type="Near Collision",
    description="Dump truck overtook light vehicle at blind corner near Pit-A junction",
    potential_severity="Critical",
    reported_by="EMP-0421",
    corrective_action="Speed restriction enforced; additional signage installed",
    shift="Day",
)

summary = tracker.get_risk_summary()
print(f"Cumulative risk score : {summary['cumulative_risk_score']}")
print(f"Top hazard type       : {summary['top_hazard']}")

# Auto-prioritized corrective actions
for action in tracker.recommend_actions():
    print(action)
```

---

## 📐 Architecture

```mermaid
graph TD
    A[📥 Input Sources\nCSV / Excel incident logs\nManual entry\nKoboToolbox field forms] --> B[SafetyIncidentTracker\nData ingestion & normalization]
    B --> C[SeverityAnalyzer\nWeighted severity scoring\nLow=1 · Med=2 · High=3 · Crit=5]
    B --> D[NearMissTracker\nProactive hazard logging\nRisk score accumulation]
    B --> E[PPEComplianceTracker\nZone-specific rules\nThreshold alerts]
    C --> F[RootCauseAnalyzer\nStructured RCA categories\nCorrectiveAction engine]
    D --> F
    E --> F
    F --> G[KPI Engine\nLTIFR · Near-miss rate\nTrend analysis · Benchmarks]
    G --> H[📊 Safety Report\nQ-o-Q trends · Priority actions\nPPE gaps · Location heat map]

    style A fill:#c0392b,color:#fff
    style H fill:#0366d6,color:#fff
    style F fill:#e67e22,color:#fff
```

---

## 📊 Demo

See [`demo/sample_output.txt`](demo/sample_output.txt) for a full Q1 2026 safety report for Pit-A North with 47 incidents, PPE compliance breakdown, and auto-generated corrective actions.

```
📋 INCIDENT SUMMARY — Pit-A North | Q1 2026
  Total Incidents         : 47       (▼ -12% vs Q4 2025 ✅)
  Lost-Time Injuries (LTI): 3
  LTI Frequency Rate      : 1.82     (benchmark: < 2.5 ✅)
  Near Misses             : 18       (▲ +20% — better reporting culture ✅)

⚠️ TOP LOCATION: Haul Road (14 incidents)
🎯 #1 Action: Speed restriction enforcement + blind corner signage [HIGH]
```

---

## 📂 Project Structure

```
mine-safety-incident-tracker/
├── src/
│   ├── main.py                           # SafetyIncidentTracker — core engine
│   ├── data_generator.py                 # Synthetic incident data generator
│   ├── safety_metrics.py                 # LTIFR, severity index calculations
│   └── analytics/
│       ├── incident_severity_analyzer.py # Weighted severity scoring
│       ├── near_miss_tracker.py          # Near-miss log + risk scoring
│       └── ppe_compliance_tracker.py     # Zone-specific PPE rules & reports
├── data/                                 # Incident CSV/Excel data (gitignored)
├── demo/                                 # Sample analysis outputs
├── examples/                             # End-to-end usage examples
├── tests/                                # pytest unit tests
├── requirements.txt
├── CHANGELOG.md
└── CONTRIBUTING.md
```

---

## 🔧 Key Modules

| Module | Description |
|--------|-------------|
| `SafetyIncidentTracker` | Load, normalize, and analyze incident records |
| `SeverityAnalyzer` | Weighted severity scoring (Low=1, Med=2, High=3, Critical=5) |
| `NearMissTracker` | Log near-miss events with hazard taxonomy and risk accumulation |
| `PPEComplianceTracker` | Zone-based PPE rules, daily compliance rate, threshold alerts |
| `RootCauseAnalyzer` | RCA category frequency analysis and corrective action prioritization |
| `SafetyMetrics` | LTIFR, TRIFR, near-miss rate, trend analysis vs industry benchmarks |

---

## 📏 Severity Weight Table

| Severity | Weight | Description |
|----------|--------|-------------|
| Low      | 1 | Minor — first aid, no lost time |
| Medium   | 2 | Moderate — medical treatment, restricted duty |
| High     | 3 | Serious — lost-time injury, hospitalization |
| Critical | 5 | Fatality or permanent disability potential |

---

## 🏷️ Near-Miss Hazard Types

`Near Collision` · `Falling Object` · `Slip/Trip` · `Equipment Malfunction` · `Electrical Hazard` · `Ground Instability` · `Dust/Gas Exposure` · `Blast Proximity` · `Unsecured Load` · `Other`

---

## 🧪 Testing

```bash
pytest tests/ -v
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

> Built by [Achmad Naufal](https://github.com/achmadnaufal) | Lead Data Analyst | Power BI · SQL · Python · GIS
