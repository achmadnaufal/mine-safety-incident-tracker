"""Mining safety performance metrics module."""
from typing import Dict
from enum import Enum


class SeverityLevel(Enum):
    """Incident severity classification."""
    FATALITY = "fatality"
    LOST_TIME_INJURY = "lost_time_injury"
    MEDICAL_TREATMENT = "medical_treatment"
    NEAR_MISS = "near_miss"


class SafetyMetricsCalculator:
    """Calculate mining safety KPIs and incident rates."""
    
    def __init__(
        self,
        mine_name: str,
        total_hours_worked: int,
        fatalities: int = 0,
        lost_time_injuries: int = 0,
        medical_treatments: int = 0,
        near_misses: int = 0,
    ):
        if total_hours_worked <= 0:
            raise ValueError("Hours worked must be positive")
        if any(x < 0 for x in [fatalities, lost_time_injuries, medical_treatments, near_misses]):
            raise ValueError("Incident counts must be non-negative")
        
        self.mine_name = mine_name
        self.total_hours_worked = total_hours_worked
        self.fatalities = fatalities
        self.lost_time_injuries = lost_time_injuries
        self.medical_treatments = medical_treatments
        self.near_misses = near_misses
    
    def calculate_trifr(self) -> float:
        """Calculate Total Recordable Incident Frequency Rate (per 1M hours)."""
        total_incidents = (
            self.fatalities +
            self.lost_time_injuries +
            self.medical_treatments
        )
        return (total_incidents / self.total_hours_worked) * 1_000_000
    
    def calculate_ltifr(self) -> float:
        """Calculate Lost Time Injury Frequency Rate (per 1M hours)."""
        total_lti = self.fatalities + self.lost_time_injuries
        return (total_lti / self.total_hours_worked) * 1_000_000
    
    def calculate_fatality_rate(self) -> float:
        """Calculate fatality rate per 1M hours."""
        return (self.fatalities / self.total_hours_worked) * 1_000_000
    
    def calculate_near_miss_ratio(self) -> float:
        """Calculate near miss to incident ratio."""
        lti = self.lost_time_injuries + self.fatalities
        if lti == 0:
            return 0 if self.near_misses == 0 else float('inf')
        return self.near_misses / lti
    
    def assess_safety_culture(self) -> str:
        """Assess mine safety culture based on metrics."""
        trifr = self.calculate_trifr()
        near_miss_ratio = self.calculate_near_miss_ratio()
        
        if trifr < 5 and near_miss_ratio > 10:
            return "excellent"
        elif trifr < 10 and near_miss_ratio > 5:
            return "good"
        elif trifr < 20:
            return "adequate"
        else:
            return "poor"
    
    def analyze(self) -> Dict:
        """Generate comprehensive safety analysis."""
        return {
            "mine_name": self.mine_name,
            "total_hours_worked": self.total_hours_worked,
            "fatalities": self.fatalities,
            "lost_time_injuries": self.lost_time_injuries,
            "medical_treatments": self.medical_treatments,
            "near_misses": self.near_misses,
            "trifr": round(self.calculate_trifr(), 2),
            "ltifr": round(self.calculate_ltifr(), 2),
            "fatality_rate_per_1m": round(self.calculate_fatality_rate(), 2),
            "near_miss_ratio": round(self.calculate_near_miss_ratio(), 2),
            "safety_culture": self.assess_safety_culture(),
        }
