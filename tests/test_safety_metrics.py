"""Tests for mining safety metrics."""
import pytest
from safety_metrics import SafetyMetricsCalculator


class TestSafetyMetricsCalculator:
    """Test safety metrics calculation."""
    
    def test_initialization_valid(self):
        """Test valid initialization."""
        calc = SafetyMetricsCalculator(
            mine_name="Mine A",
            total_hours_worked=500000,
            fatalities=1,
            lost_time_injuries=5,
        )
        assert calc.mine_name == "Mine A"
    
    def test_invalid_hours(self):
        """Test invalid hours worked."""
        with pytest.raises(ValueError):
            SafetyMetricsCalculator(
                mine_name="Mine",
                total_hours_worked=0,
            )
    
    def test_trifr_calculation(self):
        """Test TRIFR calculation."""
        calc = SafetyMetricsCalculator(
            mine_name="Mine B",
            total_hours_worked=1000000,
            fatalities=1,
            lost_time_injuries=4,
            medical_treatments=5,
        )
        trifr = calc.calculate_trifr()
        # (1+4+5) / 1M * 1M = 10
        assert trifr == pytest.approx(10.0, 0.1)
    
    def test_ltifr_calculation(self):
        """Test LTIFR calculation."""
        calc = SafetyMetricsCalculator(
            mine_name="Mine C",
            total_hours_worked=1000000,
            fatalities=0,
            lost_time_injuries=3,
        )
        ltifr = calc.calculate_ltifr()
        # (0+3) / 1M * 1M = 3
        assert ltifr == pytest.approx(3.0, 0.1)
    
    def test_fatality_rate(self):
        """Test fatality rate calculation."""
        calc = SafetyMetricsCalculator(
            mine_name="Mine D",
            total_hours_worked=500000,
            fatalities=1,
        )
        rate = calc.calculate_fatality_rate()
        # 1 / 500k * 1M = 2
        assert rate == pytest.approx(2.0, 0.1)
    
    def test_near_miss_ratio(self):
        """Test near miss ratio calculation."""
        calc = SafetyMetricsCalculator(
            mine_name="Mine E",
            total_hours_worked=1000000,
            lost_time_injuries=2,
            near_misses=20,
        )
        ratio = calc.calculate_near_miss_ratio()
        # 20 / 2 = 10
        assert ratio == pytest.approx(10.0, 0.1)
    
    def test_safety_culture_excellent(self):
        """Test excellent safety culture assessment."""
        calc = SafetyMetricsCalculator(
            mine_name="Mine F",
            total_hours_worked=1000000,
            lost_time_injuries=2,
            near_misses=50,
        )
        culture = calc.assess_safety_culture()
        # TRIFR = 2, near_miss_ratio = 25 → excellent
        assert culture == "excellent"
    
    def test_safety_culture_poor(self):
        """Test poor safety culture assessment."""
        calc = SafetyMetricsCalculator(
            mine_name="Mine G",
            total_hours_worked=100000,
            fatalities=2,
            lost_time_injuries=10,
            medical_treatments=8,
        )
        culture = calc.assess_safety_culture()
        assert culture == "poor"
    
    def test_analysis_output(self):
        """Test analysis output structure."""
        calc = SafetyMetricsCalculator(
            mine_name="Test Mine",
            total_hours_worked=750000,
            lost_time_injuries=3,
            near_misses=30,
        )
        result = calc.analyze()
        assert "trifr" in result
        assert "ltifr" in result
        assert "safety_culture" in result
        assert result["safety_culture"] in ["excellent", "good", "adequate", "poor"]
