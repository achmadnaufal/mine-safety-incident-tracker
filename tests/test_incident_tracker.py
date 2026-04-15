"""Unit tests for SafetyIncidentTracker (src/main.py).

Covers:
- Data loading (CSV, Excel, missing file, unsupported format)
- Input validation: empty DataFrame, missing columns, invalid severity,
  future dates, missing location, duplicate incident IDs
- Preprocessing: column normalisation, date parsing, whitespace stripping
- Analysis: total records, severity distribution, missing pct
- Pipeline (run()) end-to-end
- to_dataframe() export helper
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.main import SafetyIncidentTracker, VALID_SEVERITY_LEVELS, REQUIRED_COLUMNS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_csv(rows: list[dict], tmp_path: Path) -> str:
    """Write a list of dicts to a temporary CSV file and return the path."""
    df = pd.DataFrame(rows)
    path = tmp_path / "test_incidents.csv"
    df.to_csv(path, index=False)
    return str(path)


VALID_ROW = {
    "incident_id": "INC-001",
    "date": "2025-06-01",
    "severity": "High",
    "location": "Haul Road",
    "incident_type": "Near Miss",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tracker():
    return SafetyIncidentTracker()


@pytest.fixture
def valid_csv(tmp_path):
    return _make_csv([VALID_ROW], tmp_path)


@pytest.fixture
def multi_row_csv(tmp_path):
    rows = [
        {**VALID_ROW, "incident_id": f"INC-{i:03d}", "date": f"2025-0{(i % 9) + 1}-01",
         "severity": ["Low", "Medium", "High", "Critical"][i % 4]}
        for i in range(1, 9)
    ]
    return _make_csv(rows, tmp_path)


# ---------------------------------------------------------------------------
# load_data tests
# ---------------------------------------------------------------------------


class TestLoadData:
    def test_load_csv(self, tracker, valid_csv):
        df = tracker.load_data(valid_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_load_excel(self, tracker, tmp_path):
        df_orig = pd.DataFrame([VALID_ROW])
        path = str(tmp_path / "test.xlsx")
        df_orig.to_excel(path, index=False)
        df = tracker.load_data(path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_missing_file_raises(self, tracker):
        with pytest.raises(FileNotFoundError):
            tracker.load_data("/nonexistent/path/data.csv")

    def test_unsupported_format_raises(self, tracker, tmp_path):
        path = str(tmp_path / "data.txt")
        Path(path).write_text("dummy")
        with pytest.raises(ValueError, match="Unsupported file format"):
            tracker.load_data(path)

    def test_load_does_not_modify_disk(self, tracker, valid_csv):
        before = Path(valid_csv).read_text()
        tracker.load_data(valid_csv)
        after = Path(valid_csv).read_text()
        assert before == after


# ---------------------------------------------------------------------------
# validate tests
# ---------------------------------------------------------------------------


class TestValidate:
    def test_valid_dataframe_passes(self, tracker):
        df = pd.DataFrame([VALID_ROW])
        assert tracker.validate(df) is True

    def test_empty_dataframe_raises(self, tracker):
        with pytest.raises(ValueError, match="empty"):
            tracker.validate(pd.DataFrame())

    def test_missing_required_column_raises(self, tracker):
        df = pd.DataFrame([{"date": "2025-01-01", "location": "Pit"}])
        with pytest.raises(ValueError, match="missing"):
            tracker.validate(df)

    def test_invalid_severity_raises(self, tracker):
        df = pd.DataFrame([{**VALID_ROW, "severity": "Catastrophic"}])
        with pytest.raises(ValueError, match="Invalid severity"):
            tracker.validate(df)

    def test_all_valid_severity_levels_pass(self, tracker):
        for sev in VALID_SEVERITY_LEVELS:
            df = pd.DataFrame([{**VALID_ROW, "severity": sev}])
            assert tracker.validate(df) is True

    def test_future_date_raises(self, tracker):
        df = pd.DataFrame([{**VALID_ROW, "date": "2099-12-31"}])
        with pytest.raises(ValueError, match="future"):
            tracker.validate(df)

    def test_future_date_within_tolerance_passes(self, tracker):
        # Allow up to 1 day into the future
        t = SafetyIncidentTracker(config={"max_future_days": 365 * 100})
        df = pd.DataFrame([{**VALID_ROW, "date": "2090-01-01"}])
        assert t.validate(df) is True

    def test_missing_location_raises(self, tracker):
        df = pd.DataFrame([{**VALID_ROW, "location": ""}])
        with pytest.raises(ValueError, match="missing or blank location"):
            tracker.validate(df)

    def test_null_location_raises(self, tracker):
        import numpy as np
        df = pd.DataFrame([{**VALID_ROW, "location": np.nan}])
        with pytest.raises(ValueError, match="missing or blank location"):
            tracker.validate(df)

    def test_duplicate_incident_id_raises(self, tracker):
        rows = [{**VALID_ROW}, {**VALID_ROW, "date": "2025-07-01"}]
        df = pd.DataFrame(rows)
        with pytest.raises(ValueError, match="Duplicate incident_id"):
            tracker.validate(df)

    def test_unique_incident_ids_pass(self, tracker):
        rows = [
            {**VALID_ROW, "incident_id": "INC-001"},
            {**VALID_ROW, "incident_id": "INC-002", "date": "2025-07-01"},
        ]
        df = pd.DataFrame(rows)
        assert tracker.validate(df) is True


# ---------------------------------------------------------------------------
# preprocess tests
# ---------------------------------------------------------------------------


class TestPreprocess:
    def test_returns_new_dataframe(self, tracker):
        df = pd.DataFrame([VALID_ROW])
        result = tracker.preprocess(df)
        assert result is not df

    def test_column_names_normalised(self, tracker):
        df = pd.DataFrame([{"Incident ID": "INC-001", "Date": "2025-01-01",
                            "Severity": "Low", "Location": "Pit"}])
        result = tracker.preprocess(df)
        assert "incident_id" in result.columns
        assert "date" in result.columns

    def test_empty_rows_dropped(self, tracker):
        import numpy as np
        df = pd.DataFrame([VALID_ROW, {k: np.nan for k in VALID_ROW}])
        result = tracker.preprocess(df)
        assert len(result) == 1

    def test_date_column_parsed(self, tracker):
        df = pd.DataFrame([VALID_ROW])
        result = tracker.preprocess(df)
        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    def test_whitespace_stripped(self, tracker):
        df = pd.DataFrame([{**VALID_ROW, "location": "  Haul Road  "}])
        result = tracker.preprocess(df)
        assert result["location"].iloc[0] == "Haul Road"

    def test_original_dataframe_not_mutated(self, tracker):
        df = pd.DataFrame([{**VALID_ROW, "location": "  Haul Road  "}])
        original_value = df["location"].iloc[0]
        tracker.preprocess(df)
        assert df["location"].iloc[0] == original_value


# ---------------------------------------------------------------------------
# analyze tests
# ---------------------------------------------------------------------------


class TestAnalyze:
    def test_total_records_correct(self, tracker, multi_row_csv):
        df = tracker.load_data(multi_row_csv)
        result = tracker.analyze(df)
        assert result["total_records"] == 8

    def test_columns_returned(self, tracker):
        df = pd.DataFrame([VALID_ROW])
        result = tracker.analyze(df)
        assert isinstance(result["columns"], list)
        assert len(result["columns"]) > 0

    def test_missing_pct_all_present(self, tracker):
        df = pd.DataFrame([VALID_ROW])
        result = tracker.analyze(df)
        assert all(v == 0.0 for v in result["missing_pct"].values())

    def test_severity_distribution_present(self, tracker, multi_row_csv):
        df = tracker.load_data(multi_row_csv)
        result = tracker.analyze(df)
        assert "severity_distribution" in result
        assert sum(result["severity_distribution"].values()) == 8

    def test_incident_type_counts_present(self, tracker):
        rows = [
            {**VALID_ROW, "incident_id": "INC-001", "incident_type": "Near Miss"},
            {**VALID_ROW, "incident_id": "INC-002", "incident_type": "Near Miss",
             "date": "2025-07-01"},
            {**VALID_ROW, "incident_id": "INC-003", "incident_type": "Slip and Fall",
             "date": "2025-08-01"},
        ]
        df = pd.DataFrame(rows)
        result = tracker.analyze(df)
        assert result["incident_type_counts"]["Near Miss"] == 2
        assert result["incident_type_counts"]["Slip and Fall"] == 1

    def test_result_is_immutable_dict(self, tracker):
        df = pd.DataFrame([VALID_ROW])
        result = tracker.analyze(df)
        # Modifying the result should not affect calling analyze again
        result["total_records"] = 999
        result2 = tracker.analyze(df)
        assert result2["total_records"] == 1


# ---------------------------------------------------------------------------
# run() pipeline tests
# ---------------------------------------------------------------------------


class TestRun:
    def test_run_returns_dict(self, tracker, valid_csv):
        result = tracker.run(valid_csv)
        assert isinstance(result, dict)
        assert "total_records" in result

    def test_run_missing_file_raises(self, tracker):
        with pytest.raises(FileNotFoundError):
            tracker.run("/no/such/file.csv")

    def test_run_invalid_severity_raises(self, tracker, tmp_path):
        rows = [{**VALID_ROW, "severity": "FATAL"}]
        path = _make_csv(rows, tmp_path)
        with pytest.raises(ValueError, match="Invalid severity"):
            tracker.run(path)


# ---------------------------------------------------------------------------
# to_dataframe tests
# ---------------------------------------------------------------------------


class TestToDataframe:
    def test_returns_dataframe(self, tracker):
        df = pd.DataFrame([VALID_ROW])
        result = tracker.analyze(df)
        export = tracker.to_dataframe(result)
        assert isinstance(export, pd.DataFrame)
        assert "metric" in export.columns
        assert "value" in export.columns

    def test_nested_dict_flattened(self, tracker):
        df = pd.DataFrame([VALID_ROW])
        result = tracker.analyze(df)
        export = tracker.to_dataframe(result)
        metrics = export["metric"].tolist()
        # severity_distribution entries use dot notation
        assert any("severity_distribution" in m for m in metrics)
