# ETL image for the Cloud Run Job. Build context is the repo root, since
# dependencies are declared in the root pyproject.toml / uv.lock, but the
# ETL itself lives under etl/ and expects to run with that as its cwd.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code-only changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY etl/ etl/

WORKDIR /app/etl
ENV PATH="/app/.venv/bin:${PATH}"

CMD ["uv", "run", "--frozen", "--no-sync", "python", "main.py"]
