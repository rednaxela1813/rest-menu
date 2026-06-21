#!/usr/bin/env bash
# Wait for Postgres, apply migrations, collect static, then exec the CMD.
set -euo pipefail

echo "Čakám na PostgreSQL na ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}…"
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-burger}" -d "${POSTGRES_DB:-burger_menu}" >/dev/null 2>&1; do
  sleep 1
done
echo "PostgreSQL je dostupný."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
