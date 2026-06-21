#!/usr/bin/env bash
# Daily backup of PostgreSQL + media. Keeps the last 14 DB dumps.
# Run from the host:  docker compose -f docker-compose.production.yml exec django /app/compose/scripts/backup.sh
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-/app/backups}"
DB_DIR="${BACKUP_ROOT}/database"
MEDIA_DIR="${BACKUP_ROOT}/media"
KEEP="${BACKUP_KEEP:-14}"
STAMP="$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$DB_DIR" "$MEDIA_DIR"

echo "→ Záloha databázy…"
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST:-postgres}" \
    -U "${POSTGRES_USER:-burger}" \
    -d "${POSTGRES_DB:-burger_menu}" \
    | gzip > "${DB_DIR}/${STAMP}.sql.gz"
echo "  ${DB_DIR}/${STAMP}.sql.gz"

echo "→ Záloha media…"
tar -czf "${MEDIA_DIR}/${STAMP}.tar.gz" -C /app media
echo "  ${MEDIA_DIR}/${STAMP}.tar.gz"

echo "→ Rotácia (ponechať posledných ${KEEP})…"
ls -1t "${DB_DIR}"/*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
ls -1t "${MEDIA_DIR}"/*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f

echo "Hotovo. POZOR: kópie pravidelne prenášajte na druhý nosič / sieťové úložisko."
