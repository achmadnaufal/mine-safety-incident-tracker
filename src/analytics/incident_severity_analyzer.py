"""Analyze and classify safety incident severity."""

class SeverityAnalyzer:
    """Analyze incident severity patterns in mining operations."""
    
    SEVERITY_LEVELS = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    
    def __init__(self):
        self.incidents = []
    
    def add_incident(self, date: str, severity: str, 
                     description: str, injured: int = 0) -> None:
        """
        Add incident record.
        Args:
            date: Incident date (YYYY-MM-DD)
            severity: One of Low/Medium/High/Critical
            description: Incident description
            injured: Number of persons injured
        """
        if severity not in self.SEVERITY_LEVELS:
            raise ValueError(f"Invalid severity: {severity}")
        if injured < 0:
            raise ValueError("Injured count cannot be negative")
        
        self.incidents.append({
            'date': date,
            'severity': severity,
            'description': description,
            'injured': injured
        })
    
    def get_severity_distribution(self) -> dict:
        """Return count of incidents by severity level."""
        dist = {level: 0 for level in self.SEVERITY_LEVELS}
        for incident in self.incidents:
            dist[incident['severity']] += 1
        return dist
    
    def get_total_injured(self) -> int:
        """Total number of persons injured across incidents."""
        return sum(i['injured'] for i in self.incidents)
