VENV := .venv
PYTHON := $(VENV)/bin/python

.PHONY: install lint type test check demo run ui eval eval-oracle ablation db-up db-local db-down

install:
	uv venv --python 3.12 $(VENV)
	uv pip install -e ".[dev,ui]"

lint:
	$(VENV)/bin/ruff check .

type:
	$(VENV)/bin/mypy src

test:
	$(VENV)/bin/pytest -q

check: lint type test

demo:
	$(PYTHON) -m text_to_sql_engine.demo

run:
	$(VENV)/bin/uvicorn text_to_sql_engine.api:app --host 127.0.0.1 --port 8000

ui:
	$(VENV)/bin/streamlit run ui/app.py --server.port 8501

eval:
	$(PYTHON) -m evaluation.run

eval-oracle:
	$(PYTHON) -m evaluation.run --oracle

db-local:
	./scripts/setup_local_postgres.sh

RESULTS := evaluation/results

ablation:
	$(PYTHON) -m evaluation.run --prompt-mode baseline --max-corrections 0 --out $(RESULTS)/baseline_c0.json
	$(PYTHON) -m evaluation.run --prompt-mode baseline --max-corrections 2 --out $(RESULTS)/baseline_c2.json
	$(PYTHON) -m evaluation.run --prompt-mode schema_aware --max-corrections 0 --out $(RESULTS)/aware_c0.json
	$(PYTHON) -m evaluation.run --prompt-mode schema_aware --max-corrections 2 --out $(RESULTS)/aware_c2.json
	$(PYTHON) -m evaluation.compare $(RESULTS)/baseline_c0.json $(RESULTS)/aware_c0.json $(RESULTS)/baseline_c2.json $(RESULTS)/aware_c2.json

db-up:
	docker compose up -d postgres

db-down:
	docker compose down
