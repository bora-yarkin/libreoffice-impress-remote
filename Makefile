# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

.PHONY: help sdk-download oxt test lint security clean server-dev

UV ?= uv
VENV_DIR ?= .venv
SDK_DIR ?= third_party/libreoffice-sdk
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PYTEST := $(VENV_DIR)/bin/pytest
VENV_RUFF := $(VENV_DIR)/bin/ruff
VENV_REUSE := $(VENV_DIR)/bin/reuse
VENV_BANDIT := $(VENV_DIR)/bin/bandit
VENV_PIP_AUDIT := $(VENV_DIR)/bin/pip-audit
VENV_RELAY := $(VENV_DIR)/bin/impress-remote-relay
SETUP_STAMP := $(VENV_DIR)/.setup-complete

help:
	@echo "Targets: venv sdk-download oxt test lint security clean server-dev"

venv: $(SETUP_STAMP)

$(SETUP_STAMP): pyproject.toml server/pyproject.toml
	$(UV) venv $(VENV_DIR)
	$(UV) pip install --python $(VENV_PYTHON) -e '.[dev,security]' -e './server[dev]'
	@touch $(SETUP_STAMP)
	@echo "Environment ready at $(VENV_DIR)"

sdk-download: $(SETUP_STAMP)
	$(VENV_PYTHON) tools/download_sdk.py --output-dir $(SDK_DIR)

oxt: $(SETUP_STAMP)
	$(VENV_PYTHON) tools/build_oxt.py

test: $(SETUP_STAMP)
	PYTHONPATH=extension/python:server/src $(VENV_PYTEST) tests server/tests

lint: $(SETUP_STAMP)
	$(VENV_RUFF) check extension/python server/src server/tests tests tools

security: $(SETUP_STAMP)
	$(MAKE) clean
	$(VENV_REUSE) lint
	$(VENV_BANDIT) -r extension/python server/src tools -q -lll
	$(VENV_PIP_AUDIT)

server-dev: $(SETUP_STAMP)
	$(VENV_RELAY) --host-v4 0.0.0.0 --host-v6 :: --port 8080

clean:
	rm -rf dist build .pytest_cache .ruff_cache htmlcov coverage.xml
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.egg-info" -type d -prune -exec rm -rf {} +
