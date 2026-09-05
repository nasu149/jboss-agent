.PHONY: install test lint typecheck check gemini-ping app

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

app:
	streamlit run src/jboss_agent/ui/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
