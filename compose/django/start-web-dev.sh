#!/usr/bin/env bash
# Development ASGI server with autoreload.
set -euo pipefail
exec python manage.py runserver 0.0.0.0:8000
