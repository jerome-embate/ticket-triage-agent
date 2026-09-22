# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# ---- builder: resolve deps with uv, install project, pre-fetch the embedding model
FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    HF_HOME=/opt/hf-cache

WORKDIR /app

# Install dependencies first, from the lockfile only, so this layer is cached
# independently of source-code changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Now bring in the project source and install the project itself.
COPY pyproject.toml uv.lock README.md version.txt ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# knowledge_base.py loads "all-MiniLM-L6-v2" at import time; fetch it now so
# the runtime image can start with HF_HUB_OFFLINE=1 and no network access.
RUN /app/.venv/bin/python -c \
    "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ---- runtime: slim image with just the venv, the model cache, and the source
FROM base AS runtime

RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/hf-cache \
    HF_HUB_OFFLINE=1

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /opt/hf-cache /opt/hf-cache
COPY --chown=app:app src ./src

USER app

EXPOSE 8000

# ANTHROPIC_API_KEY must be supplied at runtime, e.g.
#   docker run -e ANTHROPIC_API_KEY=... -p 8000:8000 ticket-triage-agent
CMD ["uvicorn", "ticket_triage_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
