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
	reuse lint
	bandit -r extension/python server/src tools -q -lll
	pip-audit

server-dev:
	cd server && python -m impress_remote_relay --host-v4 0.0.0.0 --host-v6 :: --port 8080

clean:
	rm -rf dist build *.egg-info .pytest_cache .ruff_cache
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
