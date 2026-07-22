# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

.PHONY: help sdk-download oxt install-oxt test lint security clean refresh server-dev localization-import relay-compat

UV ?= uv
VENV_DIR ?= .venv
UV_CACHE_DIR ?= .uv-cache
SDK_DIR ?= third_party/libreoffice-sdk
LO_UNOPKG ?= $(or $(wildcard /Applications/LibreOffice.app/Contents/MacOS/unopkg),$(shell command -v unopkg 2>/dev/null))
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PYTEST := $(VENV_DIR)/bin/pytest
VENV_RUFF := $(VENV_DIR)/bin/ruff
VENV_REUSE := $(VENV_DIR)/bin/reuse
VENV_BANDIT := $(VENV_DIR)/bin/bandit
VENV_PIP_AUDIT := $(VENV_DIR)/bin/pip-audit
VENV_RELAY := $(VENV_DIR)/bin/impress-remote-relay
SETUP_STAMP := $(VENV_DIR)/.setup-complete
VERSION := $(shell cat VERSION 2>/dev/null)
OXT_FILE := dist/libreoffice-impress-remote-$(VERSION).oxt

help:
	@echo "Targets: venv sdk-download oxt install-oxt test lint security server-dev localization-import relay-compat clean refresh"

venv: $(SETUP_STAMP)

$(SETUP_STAMP): pyproject.toml server/pyproject.toml
	@if [ ! -x "$(VENV_PYTHON)" ]; then UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) venv $(VENV_DIR); fi
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) pip install --python $(VENV_PYTHON) -e '.[dev,security]' -e './server[dev]'
	@touch $(SETUP_STAMP)
	@echo "Environment ready at $(VENV_DIR)"

sdk-download: $(SETUP_STAMP)
	$(VENV_PYTHON) tools/download_sdk.py --output-dir $(SDK_DIR)

oxt: $(SETUP_STAMP)
	$(VENV_PYTHON) -m tools.build_oxt

install-oxt: oxt
	@if [ -z "$(LO_UNOPKG)" ]; then echo "LibreOffice unopkg not found. Set LO_UNOPKG=/path/to/unopkg."; exit 1; fi
	@echo "Installing $(OXT_FILE) with $(LO_UNOPKG)"
	"$(LO_UNOPKG)" add -f "$(OXT_FILE)"

test: $(SETUP_STAMP)
	PYTHONPATH=extension/python:server/src $(VENV_PYTEST) tests

lint: $(SETUP_STAMP)
	$(VENV_RUFF) check extension/python server/src tests tools

security: $(SETUP_STAMP)
	$(VENV_REUSE) lint
	$(VENV_BANDIT) -r extension/python server/src tools -q -lll
	$(VENV_PIP_AUDIT)

server-dev: $(SETUP_STAMP)
	$(VENV_RELAY) --host-v4 0.0.0.0 --host-v6 :: --port 8080

localization-import: $(SETUP_STAMP)
	$(VENV_PYTHON) -m tools.import_localizations $(ARGS)

relay-compat: $(SETUP_STAMP)
	@if [ -z "$(RELAY_URL)" ]; then echo "Set RELAY_URL=https://relay.example.com"; exit 1; fi
	$(VENV_PYTHON) -m tools.validate_relay_compat "$(RELAY_URL)"

clean:
	rm -rf dist build .pytest_cache .ruff_cache htmlcov coverage.xml $(VENV_DIR) $(UV_CACHE_DIR)
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.egg-info" -type d -prune -exec rm -rf {} +

refresh: clean venv
