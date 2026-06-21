# Zálohovanie

Záloha je pre lokálny systém **kritická**. Zálohuje sa databáza aj media súbory.

## Manuálna záloha

```bash
docker compose -f docker-compose.production.yml exec django /app/compose/scripts/backup.sh
```

Vytvorí:

```
backups/
├── database/2026-06-21_020000.sql.gz
└── media/2026-06-21_020000.tar.gz
```

Ponecháva posledných **14** databázových dumpov (premenná `BACKUP_KEEP`).

## Automatická denná záloha (cron na hostiteľovi)

```cron
0 2 * * * cd /opt/burger_menu && docker compose -f docker-compose.production.yml exec -T django /app/compose/scripts/backup.sh >> /var/log/burger-backup.log 2>&1
```

## Dôležité

- Záloha **nesmie ostať len na rovnakom disku** ako aplikácia. Pravidelne kopírujte
  priečinok `backups/` na druhý nosič alebo sieťové úložisko (NAS), napr.:

  ```bash
  rsync -a /opt/burger_menu/backups/ /mnt/nas/burger_backups/
  ```

- Zálohu pravidelne **otestujte obnovou** (viď [RESTORE.md](RESTORE.md)). Neoverená záloha
  je len nádej, nie istota.
