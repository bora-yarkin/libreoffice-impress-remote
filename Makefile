# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

.PHONY: help sdk-download oxt source-oxt install-oxt test lint security clean server-dev release-bundle cloudflare-bundle release-full

UV ?= uv
VENV_DIR ?= .venv
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
	@echo "Targets: venv sdk-download oxt source-oxt install-oxt test lint security server-dev release-bundle cloudflare-bundle release-full clean"

venv: $(SETUP_STAMP)

$(SETUP_STAMP): pyproject.toml server/pyproject.toml
	@if [ ! -x "$(VENV_PYTHON)" ]; then $(UV) venv $(VENV_DIR); fi
	$(UV) pip install --python $(VENV_PYTHON) -e '.[dev,security]' -e './server[dev]'
	@touch $(SETUP_STAMP)
	@echo "Environment ready at $(VENV_DIR)"

sdk-download: $(SETUP_STAMP)
	$(VENV_PYTHON) tools/download_sdk.py --output-dir $(SDK_DIR)

oxt: $(SETUP_STAMP)
	$(VENV_PYTHON) -m tools.build_oxt

source-oxt: $(SETUP_STAMP)
	$(VENV_PYTHON) -m tools.build_oxt --source-only

release-bundle: $(SETUP_STAMP)
	$(VENV_PYTHON) -m tools.build_release_bundle

cloudflare-bundle: $(SETUP_STAMP)
	$(VENV_PYTHON) -m tools.build_cloudflare_bundle

release-full: oxt source-oxt release-bundle cloudflare-bundle

install-oxt: oxt
	@if [ -z "$(LO_UNOPKG)" ]; then echo "LibreOffice unopkg not found. Set LO_UNOPKG=/path/to/unopkg."; exit 1; fi
	@echo "Installing $(OXT_FILE) with $(LO_UNOPKG)"
	"$(LO_UNOPKG)" add -f "$(OXT_FILE)"

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
