.PHONY: install test lint app

install:
	pip install -e '.[dev]'

test:
	pytest -q

lint:
	ruff check src tests

app:
	streamlit run src/jboss_agent/ui/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
