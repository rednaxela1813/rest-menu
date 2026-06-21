#!/usr/bin/env bash
# Restore a PostgreSQL dump produced by backup.sh.
# Usage: docker compose ... exec django /app/compose/scripts/restore.sh /app/backups/database/2026-06-21_020000.sql.gz
set -euo pipefail

DUMP="${1:?Zadajte cestu k .sql.gz súboru}"
[ -f "$DUMP" ] || { echo "Súbor neexistuje: $DUMP"; exit 1; }

echo "POZOR: tým prepíšete databázu ${POSTGRES_DB:-burger_menu}. Pokračovať? [yes/NO]"
read -r confirm
[ "$confirm" = "yes" ] || { echo "Zrušené."; exit 1; }

echo "→ Obnovujem z $DUMP …"
gunzip -c "$DUMP" | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST:-postgres}" \
    -U "${POSTGRES_USER:-burger}" \
    -d "${POSTGRES_DB:-burger_menu}"

echo "Obnova dokončená. Spustite migrácie pre istotu: python manage.py migrate"
