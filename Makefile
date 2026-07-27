.PHONY: install infra-up infra-down ingest dbt dashboard flow test lint

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip setuptools
	.venv/bin/pip install -e ".[dev]"

infra-up:
	docker compose up -d --wait

infra-down:
	docker compose down

ingest:
	.venv/bin/python -m telemetry_pipeline.ingestion --events 500

dbt:
	cd dbt_project && ../.venv/bin/dbt build

flow:
	.venv/bin/python orchestration/flow.py

dashboard:
	.venv/bin/streamlit run dashboard/app.py

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check src tests orchestration dashboard
