#!/usr/bin/env bash
set -e
echo "Waiting for database..."
python - <<'PY'
import os, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.development"))
django.setup()
from django.db import connection
for i in range(30):
    try:
        connection.ensure_connection()
        print("Database ready")
        break
    except Exception as e:
        print(f"DB not ready ({i}): {e}")
        time.sleep(2)
else:
    raise SystemExit("Database never became ready")
PY
