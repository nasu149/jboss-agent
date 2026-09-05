.PHONY: install test lint typecheck check gemini-ping step1 step2 step3 step4 step5 mcp-dev app

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

step3:
	python -m jboss_agent.cli.step3

step4:
	python -m jboss_agent.cli.step4

step5:
	python -m jboss_agent.cli.step5

mcp-dev:
	mcp dev src/jboss_agent/mcp_server/fake_jboss_server.py

app:
	streamlit run src/jboss_agent/ui/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
