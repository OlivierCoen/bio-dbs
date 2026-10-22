FROM nextflow/nextflow:26.10.3

# uv copied from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_PYTHON=3.14.9

RUN uv python install $UV_PYTHON

COPY api.py /srv/api.py
COPY pipelines/ /srv/pipelines/

RUN uv venv /srv/.venv \
    && uv pip install --python /srv/.venv/bin/python fastapi uvicorn
ENV PATH="/srv/.venv/bin:$PATH"

# Nextflow work dirs must live in the shared volume
ENV NXF_WORK=/data/dbs/.nextflow-work \
    NXF_HOME=/data/.nextflow

WORKDIR /srv
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]