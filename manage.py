#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def _use_project_venv():
    """Re-run with .venv when `python` is the system interpreter."""
    root = Path(__file__).resolve().parent
    venv_python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not venv_python.exists():
        return
    try:
        if Path(sys.executable).resolve() == venv_python.resolve():
            return
    except OSError:
        return
    os.execv(str(venv_python), [str(venv_python), *sys.argv])


def main():
    _use_project_venv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Is it installed and available on your "
            "PYTHONPATH? Did you forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
