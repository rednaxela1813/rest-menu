# Obnova zo zálohy

## Databáza

```bash
docker compose -f docker-compose.production.yml exec django \
    /app/compose/scripts/restore.sh /app/backups/database/2026-06-21_020000.sql.gz
```

Skript si vyžiada potvrdenie `yes` (prepíše aktuálnu databázu). Po obnove spustite pre istotu:

```bash
docker compose -f docker-compose.production.yml exec django python manage.py migrate
```

## Media súbory

```bash
docker compose -f docker-compose.production.yml exec django \
    tar -xzf /app/backups/media/2026-06-21_020000.tar.gz -C /app
```

## Test obnovy (odporúčaný postup)

1. Spustite druhú, testovaciu inštanciu (`POSTGRES_DB=burger_test`).
2. Obnovte do nej poslednú zálohu.
3. Prihláste sa, skontrolujte menu, počet objednávok a históriu.
4. Zaznamenajte dátum úspešného testu.

Projekt sa považuje za pripravený až keď bola záloha **overená reálnou obnovou**.
