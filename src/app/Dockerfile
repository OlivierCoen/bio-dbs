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

# needed to build properly the 'modules' package in the uv env
COPY src/modules /srv/src/modules

# mandatory to have README.md files to be able to build the package
RUN chmod +x /srv/src/app/entrypoint.sh \
    && touch /srv/src/app/README.md /srv/src/modules/README.md /srv/src/runner/README.md

RUN uv sync --frozen --no-install-project --package app

# create user, change perms
RUN groupadd app && useradd -g app -u 1000 app 

COPY --chown=app:app ./src/app /srv/src/app
COPY --chown=app:app ./src/modules /srv/src/modules

# mounting point of the static volume — otherwise Docker creates it as root when mounting it 
# we add an empty file to ensure Docker applies ownership (otherwise it skips it on the empty folder)
RUN mkdir -p /srv/src/app/static \
 && touch /srv/src/app/static/.keep \
 && chown -R app:app /srv/src/app/static

USER app

# Make the venv first in PATH so `python`, `celery`, `gunicorn`
# resolve to .venv without needing `uv run`.
ENV PATH="/srv/.venv/bin:$PATH"

WORKDIR /srv/src/app