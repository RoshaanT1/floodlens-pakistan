PY := .venv/Scripts/python

.PHONY: setup fetch data test

setup:
	python -m venv .venv && .venv/Scripts/pip install -r requirements.txt

# Network: append new raw files + manifest rows. Safe to re-run.
fetch:
	$(PY) -m src.districts fetch
	$(PY) -m src.districts build
	$(PY) -m src.forecasts fetch
	$(PY) src/fetch_imerg.py

# Offline: rebuild clean/gold layers from the frozen raw snapshot,
# verify SHA-256 against manifest, run quality checks.
data:
	$(PY) -m src.build

test:
	$(PY) -m pytest -q tests
