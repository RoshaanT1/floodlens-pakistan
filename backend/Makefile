# Windows venvs put binaries in Scripts/, POSIX ones in bin/.
ifeq ($(OS),Windows_NT)
VENV_BIN := .venv/Scripts
PYTHON := python
else
VENV_BIN := .venv/bin
PYTHON := python3
endif
PY := $(VENV_BIN)/python

.PHONY: setup fetch data test

setup:
	$(PYTHON) -m venv .venv && $(VENV_BIN)/pip install -r requirements.txt

# Network: append new raw files + manifest rows. Safe to re-run.
fetch:
	$(PY) -m src.districts fetch
	$(PY) -m src.districts build
	$(PY) -m src.forecasts fetch
	$(PY) -m src.imerg fetch

# Offline: rebuild clean/gold layers from the frozen raw snapshot,
# verify SHA-256 against manifest, run quality checks.
data:
	$(PY) -m src.build

test:
	$(PY) -m pytest -q tests
