FROM python:3.12-slim

# uv copied from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy metadata first for Docker layer caching:
# dependencies are only reinstalled when pyproject/uv.lock change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Then add the project itself to the same venv
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Make the venv first in PATH so `python`, `celery`, `gunicorn`
# resolve to .venv without needing `uv run`.
ENV PATH="/app/.venv/bin:$PATH"

RUN chmod +x entrypoint.sh

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]