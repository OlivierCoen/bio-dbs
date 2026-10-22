#!/bin/sh
set -e

if [ -d "static" ]; then
    echo "Static directory already exists, skipping static files collection."
else
    echo "Static directory does not exist, collecting static files."
    python manage.py collectstatic
fi

echo "Migrating database..."
python manage.py migrate
echo "Creating superuser..."
python manage.py createsuperuser --noinput || echo "Super user already exists"
echo "Starting server..."
python manage.py runserver 0.0.0.0:8000