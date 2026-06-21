#!/usr/bin/env bash
# ASGI server (Daphne) serving HTTP + WebSocket for Django Channels.
set -euo pipefail
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
