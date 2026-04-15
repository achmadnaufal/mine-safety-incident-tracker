"""
Mining safety incident tracking, classification, and trend analysis system.

This module provides the core ``SafetyIncidentTracker`` class, which is the
primary entry point for loading, validating, preprocessing, and analysing
incident record datasets for open-cut and underground coal mining operations.

Typical usage::

    from src.main import SafetyIncidentTracker

    tracker = SafetyIncidentTracker()
    result = tracker.run("data/sample_incidents.csv")
    print(result["total_records"])

Author: github.com/achmadnaufal
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SEVERITY_LEVELS: frozenset = frozenset({"Low", "Medium", "High", "Critical"})
VALID_STATUSES: frozenset = frozenset({"Open", "Closed", "Under Investigation", "In Progress"})
REQUIRED_COLUMNS: Tuple[str, ...] = ("incident_id", "date", "severity")


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class SafetyIncidentTracker:
    """Mine safety incident tracker — load, validate, preprocess, and analyse
    incident records from CSV or Excel files.

    The tracker enforces immutable data patterns: all transformations return
    new DataFrames without modifying the original input.

    Attributes:
        config (dict): Optional configuration overrides.

    Example::

        tracker = SafetyIncidentTracker()
        df = tracker.load_data("demo/sample_data.csv")
        result = tracker.analyze(df)
        print(result["total_records"])
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialise the tracker with an optional configuration dict.

        Args:
            config: Optional mapping of configuration keys to values.
                Supported keys:

                - ``"required_columns"`` – iterable of column names that must
                  be present after normalisation (default: ``REQUIRED_COLUMNS``).
                - ``"max_future_days"`` – number of days ahead of today that a
                  date field is allowed to be (default: ``0``).
        """
        self.config: Dict[str, Any] = config or {}

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load incident records from a CSV or Excel file.

        The file is read but *not* modified.  A fresh DataFrame is returned
        each call.

        Args:
            filepath: Absolute or relative path to a ``.csv``, ``.xlsx``, or
                ``.xls`` file.

        Returns:
            Raw DataFrame exactly as loaded from disk.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file extension is not supported.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        suffix = path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(filepath)
        if suffix == ".csv":
            return pd.read_csv(filepath)
        raise ValueError(
            f"Unsupported file format '{suffix}'. Expected .csv, .xlsx, or .xls."
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate the structure and content of an incident DataFrame.

        Checks performed:

        1. DataFrame must not be empty.
        2. After column normalisation, all *required* columns must be present.
        3. If a ``severity`` column exists, all values must be in
           ``VALID_SEVERITY_LEVELS``.
        4. If a ``date`` column exists, no date may be in the future beyond
           the configured ``max_future_days`` tolerance.
        5. If a ``location`` column exists, it must not contain blank entries.
        6. If an ``incident_id`` column exists, all IDs must be unique.

        Args:
            df: Raw or preprocessed incident DataFrame.

        Returns:
            ``True`` when all checks pass.

        Raises:
            ValueError: With a descriptive message for each failed check.
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty.")

        normalised_cols = [c.lower().strip().replace(" ", "_") for c in df.columns]

        required = self.config.get("required_columns", REQUIRED_COLUMNS)
        missing_cols = [c for c in required if c not in normalised_cols]
        if missing_cols:
            raise ValueError(
                f"Required column(s) missing after normalisation: {missing_cols}"
            )

        # Map original column names to normalised equivalents for lookups
        col_map: Dict[str, str] = {
            norm: orig
            for orig, norm in zip(df.columns, normalised_cols)
        }

        # Severity validation
        if "severity" in col_map:
            sev_col = col_map["severity"]
            bad = df[sev_col].dropna()
            invalid = bad[~bad.isin(VALID_SEVERITY_LEVELS)]
            if not invalid.empty:
                raise ValueError(
                    f"Invalid severity value(s): {invalid.unique().tolist()}. "
                    f"Allowed: {sorted(VALID_SEVERITY_LEVELS)}"
                )

        # Future date validation
        if "date" in col_map:
            max_future = self.config.get("max_future_days", 0)
            date_col = col_map["date"]
            parsed = pd.to_datetime(df[date_col], errors="coerce")
            cutoff = pd.Timestamp(datetime.date.today()) + pd.Timedelta(days=max_future)
            future = parsed[parsed > cutoff]
            if not future.empty:
                raise ValueError(
                    f"{len(future)} record(s) have dates in the future "
                    f"(beyond {cutoff.date()})."
                )

        # Missing location validation
        if "location" in col_map:
            loc_col = col_map["location"]
            blank = df[loc_col].isnull() | (df[loc_col].astype(str).str.strip() == "")
            if blank.any():
                raise ValueError(
                    f"{blank.sum()} record(s) have missing or blank location data."
                )

        # Duplicate incident ID check
        if "incident_id" in col_map:
            id_col = col_map["incident_id"]
            dupes = df[id_col].dropna()
            dupes = dupes[dupes.duplicated()]
            if not dupes.empty:
                raise ValueError(
                    f"Duplicate incident_id value(s) found: {dupes.unique().tolist()}"
                )

        return True

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalise an incident DataFrame.

        This method is *non-mutating*: it returns a new DataFrame and never
        modifies the input.

        Transformations applied:

        - Drop rows that are entirely empty.
        - Normalise column names to lowercase, stripped, underscore-spaced.
        - Parse any column named ``date`` to ``datetime64``.
        - Strip leading/trailing whitespace from string columns.

        Args:
            df: Raw DataFrame as returned by :meth:`load_data`.

        Returns:
            A new, cleaned DataFrame.
        """
        cleaned = df.copy()
        cleaned = cleaned.dropna(how="all")
        cleaned = cleaned.rename(
            columns={c: c.lower().strip().replace(" ", "_") for c in cleaned.columns}
        )

        if "date" in cleaned.columns:
            cleaned = cleaned.assign(date=pd.to_datetime(cleaned["date"], errors="coerce"))

        # Strip strings without mutating in-place
        str_cols = cleaned.select_dtypes(include="object").columns.tolist()
        str_updates = {col: cleaned[col].str.strip() for col in str_cols}
        if str_updates:
            cleaned = cleaned.assign(**str_updates)

        return cleaned

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run core statistical analysis on an incident DataFrame.

        Args:
            df: Raw or partially processed incident DataFrame.

        Returns:
            A dict containing:

            - ``"total_records"`` (int) – row count after cleaning.
            - ``"columns"`` (list) – normalised column names.
            - ``"missing_pct"`` (dict) – column → percentage of missing values.
            - ``"summary_stats"`` (dict, optional) – describe() output for
              numeric columns.
            - ``"totals"`` (dict, optional) – column sums for numeric columns.
            - ``"means"`` (dict, optional) – column means for numeric columns.
            - ``"severity_distribution"`` (dict, optional) – count per severity
              level when a ``severity`` column is present.
            - ``"incident_type_counts"`` (dict, optional) – count per
              ``incident_type`` when that column exists.
        """
        processed = self.preprocess(df)
        result: Dict[str, Any] = {
            "total_records": len(processed),
            "columns": list(processed.columns),
            "missing_pct": (
                processed.isnull().sum() / max(len(processed), 1) * 100
            ).round(1).to_dict(),
        }

        numeric_df = processed.select_dtypes(include="number")
        if not numeric_df.empty:
            result["summary_stats"] = numeric_df.describe().round(3).to_dict()
            result["totals"] = numeric_df.sum().round(2).to_dict()
            result["means"] = numeric_df.mean().round(3).to_dict()

        if "severity" in processed.columns:
            result["severity_distribution"] = (
                processed["severity"].value_counts().to_dict()
            )

        if "incident_type" in processed.columns:
            result["incident_type_counts"] = (
                processed["incident_type"].value_counts().to_dict()
            )

        return result

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def run(self, filepath: str) -> Dict[str, Any]:
        """Execute the full pipeline: load → validate → analyse.

        Args:
            filepath: Path to the incident data file (.csv, .xlsx, or .xls).

        Returns:
            Analysis result dict as produced by :meth:`analyze`.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If validation fails.
        """
        raw = self.load_data(filepath)
        preprocessed = self.preprocess(raw)
        self.validate(preprocessed)
        return self.analyze(preprocessed)

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def to_dataframe(self, result: Dict[str, Any]) -> pd.DataFrame:
        """Flatten an analysis result dict into a two-column DataFrame.

        Nested dicts are expanded as ``"parent_key.child_key"`` rows.

        Args:
            result: Dict as returned by :meth:`analyze`.

        Returns:
            DataFrame with columns ``["metric", "value"]``.
        """
        rows: List[Dict[str, Any]] = []
        for key, value in result.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    rows.append({"metric": f"{key}.{sub_key}", "value": sub_value})
            else:
                rows.append({"metric": key, "value": value})
        return pd.DataFrame(rows)
