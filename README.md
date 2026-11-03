# Bio-dbs

Standalone server for fetching, downloading and managing bioinformatics database locally.

## Usage

>[!NOTE]
>The `bio-dbs` server must be launched using `docker compose`. In case it is not installed on your computer, check the [official Docker instructions](https://docs.docker.com/compose/install/).

To launch the app (production):
```
# from the repository root folder
docker compose up
```

## Development

>[!NOTE]
>You need `uv` for developping the app. See [here](https://docs.astral.sh/uv/getting-started/installation/) for install instructions.
>To build the current environment, do:
> ```
>uv sync --frozen --no-install-project
>```

To launch the app in dev mode:
```
docker compose -f docker-compose.yml -f docker-compose.dev.yml up [--build]
```

To delete persistent volumes and create a fresh app ready for new modifications:
```
docker compose down \
  && docker volume prune -a -f \
  && cd src/app \
  && uv run python manage.py makemigrations databases \
  && cd ...
```