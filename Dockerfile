FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install Python dependencies during image build so the Dev Container opens with
# LangGraph / Gemini / Streamlit already available. .env is intentionally never copied.
COPY pyproject.toml /tmp/langgraph-jboss-agent/pyproject.toml
COPY src /tmp/langgraph-jboss-agent/src
RUN cd /tmp/langgraph-jboss-agent \
    && pip install --upgrade pip \
    && pip install '.[dev]' \
    && rm -rf /tmp/langgraph-jboss-agent

EXPOSE 8501

WORKDIR /workspace
CMD ["bash"]
