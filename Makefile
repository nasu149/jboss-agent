.PHONY: install test lint typecheck check gemini-ping step1 step2 app

install:
	pip install -e '.[dev]'

test:
	pytest -q

lint:
	ruff check src tests

typecheck:
	mypy src

check: lint test

gemini-ping:
	python -m jboss_agent.cli.gemini_ping

step1:
	python -m jboss_agent.cli.step1

SCENARIO ?= thread_pool
step2:
	python -m jboss_agent.cli.step2 --scenario $(SCENARIO)

app:
	streamlit run src/jboss_agent/ui/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
