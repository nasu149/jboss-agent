.PHONY: install test lint typecheck check gemini-ping step1 step2 step3 step4 step5 step6 step7 step8 step9 step7-pause step7-resume mcp-dev app

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

step6:
	python -m jboss_agent.cli.step6

step7:
	python -m jboss_agent.cli.step7

step8:
	python -m jboss_agent.cli.step8

step9:
	python -m jboss_agent.cli.step9

STEP7_THREAD_ID ?= incident:step7-durable-demo
step7-pause:
	CHECKPOINT_BACKEND=sqlite python -m jboss_agent.cli.step7 --pause-only --thread-id $(STEP7_THREAD_ID)

step7-resume:
	CHECKPOINT_BACKEND=sqlite python -m jboss_agent.cli.step7 --resume-only --thread-id $(STEP7_THREAD_ID) --decision approve

mcp-dev:
	mcp dev src/jboss_agent/mcp_server/fake_jboss_server.py

app:
	streamlit run src/jboss_agent/ui/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
