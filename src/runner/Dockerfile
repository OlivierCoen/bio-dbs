FROM python:3.14-slim

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
COPY src/app/pyproject.toml /srv/src/app/
COPY src/runner/pyproject.toml /srv/src/runner/
COPY src/modules/pyproject.toml /srv/src/modules/

# mandatory to be able to build the package
RUN touch /srv/src/app/README.md /srv/src/modules/README.md /srv/src/runner/README.md

RUN uv sync --frozen --no-install-project --package runner

COPY ./src/app /srv/src/app
COPY ./src/modules /srv/src/modules

ENV PATH="/srv/.venv/bin:$PATH"

# allows workers to resolve models and access postgres db
ENV DJANGO_SETTINGS_MODULE=configs.settings 

WORKDIR /srv/src/app