"""WSGI config for local web app."""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tal_maria_ikea.web.project.settings")

application = get_wsgi_application()
