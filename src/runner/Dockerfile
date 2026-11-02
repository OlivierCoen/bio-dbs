FROM python:3.14.9-slim

# epel-release is needed to install aria2 in this base image
RUN apt update && apt install -y \
    aria2 \
    pigz

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
RUN groupadd appuser && useradd -r -g appuser -u 1000 appuser 

COPY --chown=appuser:appuser ./src/app /srv/src/app

# create persistent volume for databases and change its owner
# so that it get writable
RUN mkdir -p /data/dbs \
    && chown appuser:appuser /data/dbs

USER appuser

ENV PATH="/srv/.venv/bin:$PATH"

# allows workers to resolve models and access postgres db
ENV DJANGO_SETTINGS_MODULE=configs.settings 

WORKDIR /srv/src/app