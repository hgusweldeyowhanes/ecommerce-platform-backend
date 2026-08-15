#!/bin/sh
set -e
mkdir -p /app/media /app/staticfiles
./scripts/wait_for_db.sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
if [ "${SEED_CATALOG:-False}" = "True" ] || [ "${SEED_CATALOG:-false}" = "true" ]; then
  python manage.py seed_catalog
fi
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout 60 \
  --access-logfile -
