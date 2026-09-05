FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml /tmp/pyproject.toml
COPY src/jboss_agent/__init__.py /tmp/src/jboss_agent/__init__.py

RUN cd /tmp \
    && pip install --upgrade pip \
    && pip install -e ".[dev]"

WORKDIR /workspace

CMD ["bash"]
