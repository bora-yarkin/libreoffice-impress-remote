# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

.PHONY: help oxt test lint security clean server-dev

help:
	@echo "Targets: oxt test lint security clean server-dev"

oxt:
	python tools/build_oxt.py

test:
	PYTHONPATH=extension/python:server/src pytest tests server/tests

lint:
	ruff check extension/python server/src server/tests tests tools

security:
	make clean
	reuse lint
	bandit -r extension/python server/src tools -q -lll
	pip-audit

server-dev:
	cd server && python -m impress_remote_relay --host-v4 0.0.0.0 --host-v6 :: --port 8080

clean:
	rm -rf dist build .pytest_cache .ruff_cache htmlcov coverage.xml
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.egg-info" -type d -prune -exec rm -rf {} +
