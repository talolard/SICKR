"""Convenience launcher for local Django runserver."""

from __future__ import annotations

import argparse
import os

from django.core.management import execute_from_command_line


def main() -> None:
    """Parse args and run Django development server."""

    parser = argparse.ArgumentParser(description="Run local Django web server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="8000")
    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tal_maria_ikea.web.project.settings")
    execute_from_command_line(["manage.py", "migrate", "--noinput"])
    execute_from_command_line(["manage.py", "runserver", f"{args.host}:{args.port}"])


if __name__ == "__main__":
    main()
