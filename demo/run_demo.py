#!/usr/bin/env python3
"""
Mine Safety Incident Tracker — Demo
Runs near-miss tracking and PPE compliance analysis from sample data.
"""
import sys
from pathlib import Path
import csv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.near_miss_tracker import NearMissTracker
from src.analytics.ppe_compliance_tracker import PPEComplianceTracker, InspectionRecord


def main():
    print("=" * 64)
    print("  Mine Safety Incident Tracker — Demo")
    print("  Site: Pit-A North | Period: Q1 2026")
    print("=" * 64)
    print()

    # ── Near Miss Tracker ────────────────────────────────────────
    tracker = NearMissTracker(site_name="Pit-A North")

    # Load sample incident data
    data_path = Path(__file__).parent.parent / "data" / "sample_incidents.csv"
    events_loaded = 0
    with open(data_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tracker.record_event(
                date=row["date"],
                area=row["area"],
                hazard_type=row["hazard_type"],
                description=row["description"],
                potential_severity=row["potential_severity"],
                reported_by=row["reported_by"],
                corrective_action=row["corrective_action"],
                shift=row["shift"],
            )
            events_loaded += 1

    summary = tracker.get_risk_summary()
    actions = tracker.recommend_actions()

    print(f"✓ Loaded {events_loaded} incident records from sample_incidents.csv")
    print()
    print("Incident Summary:")
    print(f"  Site                  : {summary['site']}")
    print(f"  Total events logged   : {summary['total_events']}")
    print(f"  Cumulative risk score : {summary['cumulative_risk_score']}")
    print(f"  Top hazard type       : {summary['top_hazard']}")
    print(f"  Top location          : {summary['top_area']}")
    print(f"  Night shift events    : {summary['night_shift_pct']:.0f}%")
    print()

    print("Severity Distribution:")
    for sev, cnt in sorted(summary["severity_distribution"].items(),
                           key=lambda x: ["Critical","High","Medium","Low"].index(x[0])
                           if x[0] in ["Critical","High","Medium","Low"] else 99):
        bar = "█" * cnt
        print(f"  {sev:<10} {bar:<20} {cnt:>3}")
    print()

    print("Hazard Frequency:")
    sorted_hazards = sorted(summary["hazard_counts"].items(), key=lambda x: -x[1])
    for hazard, cnt in sorted_hazards[:5]:
        print(f"  {hazard:<25} : {cnt}")
    print()

    print("Top Recommended Corrective Actions:")
    for i, action in enumerate((actions or ["No actions available"])[:3], 1):
        print(f"  {i}. {action}")
    print()

    # ── PPE Compliance ───────────────────────────────────────────
    print("─" * 64)
    ppe = PPEComplianceTracker(site_id="Pit-A North")

    inspections = [
        ("W001", "2026-03-11", ["head", "body", "foot", "hand", "eye"], "open_cut"),
        ("W002", "2026-03-11", ["head", "body", "foot"], "open_cut"),
        ("W003", "2026-03-11", ["head", "body", "foot", "hand", "eye", "hearing"], "wash_plant"),
        ("W004", "2026-03-11", ["head", "body"], "open_cut"),
        ("W005", "2026-03-11", ["head", "body", "foot", "hand"], "workshop"),
        ("W006", "2026-03-11", ["head", "body", "foot", "hand", "eye", "hearing"], "open_cut"),
        ("W007", "2026-03-11", ["head", "body", "foot", "hand"], "open_cut"),
        ("W008", "2026-03-11", ["head", "body", "foot", "hand", "eye"], "workshop"),
    ]
    for w in inspections:
        rec = InspectionRecord(worker_id=w[0], date=w[1], ppe_worn=w[2], zone=w[3])
        ppe.log_inspection(rec)

    report = ppe.daily_report("2026-03-11")
    print()
    print("PPE Compliance Report (2026-03-11):")
    print(f"  Workers inspected     : {report['inspections']}")
    print(f"  Fully compliant       : {report['fully_compliant']}")
    print(f"  Violations            : {report['violations']}")
    print(f"  Compliance rate       : {report['compliance_rate_pct']:.1f}%")
    if report["most_missed_ppe"]:
        missed = ", ".join(f"{item[0]} (×{item[1]})" for item in report["most_missed_ppe"][:3])
        print(f"  Most missed PPE       : {missed}")
    print()
    if report["alerts"]:
        print("⚠️  Alerts:")
        for alert in report["alerts"]:
            print(f"  {alert}")
        print()

    print("=" * 64)
    print("  ✅ Demo complete")
    print("=" * 64)


if __name__ == "__main__":
    main()
