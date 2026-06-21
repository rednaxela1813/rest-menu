# Inštalácia a lokálne nasadenie

## Hardvér

Odporúčaný mini-PC / Intel NUC so SSD a Linuxom. Raspberry Pi 5 so SSD je možný, ale
microSD sa neodporúča (opotrebovanie a riziko straty dát).

## Sieť

```
Wi-Fi router
├── Lokálny server (statická IP, napr. 192.168.1.50)
├── Tablet pokladne
├── Tablet kuchyne
├── Telefóny hostí
└── Tablety pri stoloch
```

1. Nastavte serveru **statickú IP** v routeri (DHCP rezervácia).
2. Voliteľne pridajte do routera lokálne meno `menu.local` → IP servera.
3. Do `.env` doplňte IP/meno do `DJANGO_ALLOWED_HOSTS` a `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Inštalácia

```bash
git clone <repo> && cd burger_menu
cp .env.example .env            # SECRET_KEY, heslá, ALLOWED_HOSTS
docker compose -f docker-compose.production.yml up -d --build
```

Entrypoint automaticky spustí `migrate` a `collectstatic`. Vytvorte administrátora a dáta:

```bash
docker compose -f docker-compose.production.yml exec django python manage.py createsuperuser
docker compose -f docker-compose.production.yml exec django python manage.py seed_demo   # voliteľné demo
```

## Automatický štart po reštarte

Kontajnery majú `restart: unless-stopped`, takže po reštarte servera nabehnú samy.
Skontrolujte, že Docker beží pri štarte systému:

```bash
sudo systemctl enable docker
```

## Health-check

```bash
curl http://192.168.1.50/health/
# {"django":"ok","database":"ok","channel_layer":"ok","status":"ok"}
```

Kontajnery `django` a `postgres`/`redis` majú aj Docker healthcheck (`docker compose ps`).

## QR kódy pre stoly

V admine (Stoly) stiahnete PNG pre jeden stôl, alebo PDF všetkých aktívnych stolov:
`/staff/tables/qr.pdf`. Na výtlačku je text *„Naskenujte QR kód a objednajte si“* a číslo stola.

## Kiosk mód (tablety)

- **Pokladňa**: prehliadač v kiosk/fullscreen móde na `/staff/cashier/orders/`, trvalá session.
- **Kuchyňa**: `/staff/kitchen/orders/`, tlačidlo ⛶ prepne na celú obrazovku.
- Tablet pri stole: zafixujte URL `/table/<číslo>/<token>/`.

## Práca bez internetu

Všetky CSS/JS/obrázky/fonty sú lokálne (žiadne CDN). Pokým je server, router a zariadenia
v jednej sieti, systém funguje aj bez prístupu na internet.
