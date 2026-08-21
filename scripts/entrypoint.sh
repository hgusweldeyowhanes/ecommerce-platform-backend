#!/bin/sh
set -e
mkdir -p /app/media /app/staticfiles
./scripts/wait_for_db.sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
if [ "${SEED_CATALOG:-True}" = "True" ] || [ "${SEED_CATALOG:-true}" = "true" ]; then
  # --replace hides old Adera demo SKUs; --force-images rewrites media after Render's
  # ephemeral disk wipe so Google Drive seed photos stay available.
  python manage.py seed_catalog --replace --force-images
fi
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout 60 \
  --access-logfile -
