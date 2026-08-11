"""Standalone seed helper (also available as manage.py seed_catalog)."""
import os
import sys

import django

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.core.management import call_command

if __name__ == "__main__":
    call_command("seed_catalog")
