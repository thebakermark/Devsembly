FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git gh ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv pip install --system .

COPY devsembly ./devsembly
COPY tests ./tests

CMD ["uvicorn", "devsembly.api:app", "--host", "0.0.0.0", "--port", "8000"]
