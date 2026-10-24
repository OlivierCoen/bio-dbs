FROM python:3.14-slim

# uv copied from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /srv

# Copy metadata first for Docker layer caching:
# dependencies are only reinstalled when pyproject/uv.lock change.
COPY pyproject.toml uv.lock /srv/
COPY src/app/pyproject.toml src/app/entrypoint.sh /srv/src/app/
COPY src/runner/pyproject.toml /srv/src/runner/
COPY src/modules/pyproject.toml /srv/src/modules/

RUN chmod +x /srv/src/app/entrypoint.sh

# mandatory to be able to build the package
RUN touch /srv/src/app/README.md /srv/src/modules/README.md /srv/src/runner/README.md

RUN uv sync --frozen --no-install-project --package app

COPY ./src/app /srv/src/app
COPY ./src/modules /srv/src/modules

# Make the venv first in PATH so `python`, `celery`, `gunicorn`
# resolve to .venv without needing `uv run`.
ENV PATH="/srv/.venv/bin:$PATH"

WORKDIR /srv/src/app