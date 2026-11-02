FROM python:3.14.9-slim

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

RUN uv sync --python /usr/local/bin/python --frozen --no-install-project

# create user, change perms
RUN groupadd appuser && useradd -g appuser -u 1000 appuser 

COPY --chown=appuser:appuser ./src/app /srv/src/app

# create persistent volume for databases and change its owner
# so that it get writable
RUN mkdir -p /data/dbs \
    && chown appuser:appuser /data/dbs

# mounting point of the static volume — otherwise Docker creates it as root when mounting it 
# we add an empty file to ensure Docker applies ownership (otherwise it skips it on the empty folder)
RUN mkdir -p /srv/src/app/static \
 && touch /srv/src/app/static/.keep \
 && chown -R appuser:appuser /srv/src/app/static

RUN mkdir -p /data/dbs && chown appuser:appuser /data/dbs

USER appuser

# Make the venv first in PATH so `python`, `celery`, `gunicorn`
# resolve to .venv without needing `uv run`.
ENV PATH="/srv/.venv/bin:$PATH"

RUN chmod +x /srv/src/app/entrypoint.sh

WORKDIR /srv/src/app