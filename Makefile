PY := .venv/bin/python

.PHONY: setup fetch data test

setup:
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Network: append new raw files + manifest rows. Safe to re-run.
fetch:
	$(PY) -m src.districts fetch
	$(PY) -m src.districts build
	$(PY) -m src.forecasts fetch

# Offline: rebuild clean/gold layers from the frozen raw snapshot.
data:
	$(PY) -m src.build

test:
	$(PY) -m pytest -q tests
