"""Convenience launcher for local Django runserver."""

from __future__ import annotations

import argparse
import os

import django
from django.contrib.auth import get_user_model
from django.core.management import execute_from_command_line


def _ensure_local_admin_user() -> None:
    """Create or update a predictable local superuser for admin access."""

    username = os.environ.get("DJANGO_ADMIN_USERNAME", "admin")
    password = os.environ.get("DJANGO_ADMIN_PASSWORD", "admin")
    email = os.environ.get("DJANGO_ADMIN_EMAIL", "admin@example.local")

    user_model = get_user_model()
    user = user_model.objects.filter(username=username).first()
    if user is None:
        user_model.objects.create_superuser(username=username, email=email, password=password)
        return

    user.is_superuser = True
    user.is_staff = True
    user.set_password(password)
    user.email = email
    user.save(update_fields=["is_superuser", "is_staff", "password", "email"])


def main() -> None:
    """Parse args and run Django development server."""

    parser = argparse.ArgumentParser(description="Run local Django web server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="8000")
    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tal_maria_ikea.web.project.settings")
    execute_from_command_line(["manage.py", "migrate", "--noinput"])
    django.setup()
    _ensure_local_admin_user()
    execute_from_command_line(["manage.py", "runserver", f"{args.host}:{args.port}"])


if __name__ == "__main__":
    main()
