FROM python:3.12-slim

ARG CLAUDE_CODE_VERSION=2.1.220

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISABLE_AUTOUPDATER=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git gh ca-certificates nodejs npm \
    && npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && rm -rf /var/lib/apt/lists/* /root/.npm
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv pip install --system .

COPY devsembly ./devsembly
COPY scripts ./scripts
COPY tests ./tests
RUN chmod 0755 /app/scripts/providers/*.sh

CMD ["uvicorn", "devsembly.api:app", "--host", "0.0.0.0", "--port", "8000"]
