import pytest
from src.analytics.incident_severity_analyzer import SeverityAnalyzer

def test_add_incident():
    analyzer = SeverityAnalyzer()
    analyzer.add_incident("2026-03-01", "High", "Equipment failure", injured=2)
    assert len(analyzer.incidents) == 1
    assert analyzer.incidents[0]['injured'] == 2

def test_invalid_severity():
    analyzer = SeverityAnalyzer()
    with pytest.raises(ValueError):
        analyzer.add_incident("2026-03-01", "Unknown", "Test")

def test_severity_distribution():
    analyzer = SeverityAnalyzer()
    analyzer.add_incident("2026-03-01", "High", "Incident 1")
    analyzer.add_incident("2026-03-02", "Low", "Incident 2")
    analyzer.add_incident("2026-03-03", "High", "Incident 3")
    
    dist = analyzer.get_severity_distribution()
    assert dist["High"] == 2
    assert dist["Low"] == 1

def test_total_injured():
    analyzer = SeverityAnalyzer()
    analyzer.add_incident("2026-03-01", "High", "Inc1", injured=2)
    analyzer.add_incident("2026-03-02", "Critical", "Inc2", injured=3)
    assert analyzer.get_total_injured() == 5
