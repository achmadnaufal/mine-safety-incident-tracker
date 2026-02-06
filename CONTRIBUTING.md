# Contributing to Mine Safety Incident Tracker

Thank you for your interest in contributing! This project helps mining operations track, classify, and analyze safety incidents to build a safer workplace culture. Contributions to analytics modules, new hazard classifications, reporting improvements, and documentation are welcome.

## Getting Started

1. Fork the repository and clone your fork
2. Create a virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Create a branch: `git checkout -b feature/your-feature-name`

## Development Guidelines

- **Tests required** — all new analytics modules need `pytest` unit tests in `tests/`
- **Safety standards** — align incident classifications with ICMM Safety Performance Framework
- **Data privacy** — never commit real incident data; use the `data_generator.py` for samples
- **Severity scoring** — follow the established weight table (Low=1, Medium=2, High=3, Critical=5)

## Submitting Changes

1. Run tests: `pytest tests/ -v`
2. Update `CHANGELOG.md`
3. Open a pull request describing the change

## Domain Context

This system supports open-cut coal mining operations. Incident categories and severity levels follow common industry frameworks (ICMM, Queensland mine safety regulations). New hazard types should reference applicable standards.

## Reporting Bugs

Open an issue with Python version, sample input CSV (no real data), and full error traceback.
