#!/bin/sh
set -e

# attendre que la DB soit prête ET les migrations appliquées
until python manage.py migrate --check --noinput >/dev/null 2>&1; do
  echo "waiting for migrations..."
  sleep 2
done

exec "$@"