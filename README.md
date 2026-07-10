# Burger Menu — lokálny systém elektronického menu a príjmu objednávok

Samostatné webové aplikácie pre burgeráreň, ktoré nahrádza papierové menu a umožňuje
hosťom objednávať cez QR kód alebo tablet. Objednávky sa v reálnom čase zobrazujú na
pokladni a v kuchyni. Funguje **lokálne, bez internetu** (LAN).

Cyklus: **hosť → košík → objednávka → pokladňa → kuchyňa → hotové → vydané**.

---

## Technológie

- Python 3.13, Django 5.x
- PostgreSQL, Redis, Django Channels (WebSocket + HTMX/polling fallback)
- Django Templates + vanilla JS (žiadne CDN — všetko lokálne)
- Docker / Docker Compose, Nginx, Daphne (ASGI)
- pytest, factory_boy, Ruff, mypy, pre-commit

## Štruktúra

```
config/            # nastavenia (base/local/production/test), urls, asgi, wsgi
apps/
  accounts/        # používateľ s rolami (admin, cashier, kitchen, waiter)
  restaurants/     # prevádzka + health-check
  tables/          # stoly, QR tokeny, generovanie QR (PNG/PDF)
  menu/            # kategórie, položky, alergény, modifikátory
  orders/          # objednávky, stavový automat, services, selectors, košík
  cashier/         # kanban pokladne
  kitchen/         # kuchynský displej
  notifications/   # WebSocket consumers + broadcast udalostí
  audit/           # denník akcií
templates/  static/  tests/  compose/  docs/
```

Architektúra dodržiava oddelenie vrstiev: `models.py`, `services.py` (business logika a
zmeny stavov), `selectors.py` (čítacie dotazy), `cart.py`, `consumers.py`. Šablóny ani
view neobsahujú kritickú business logiku.

---

## Rýchly štart (Docker)

```bash
cp .env.example .env          # upravte heslá a SECRET_KEY
docker compose -f docker-compose.local.yml up --build
```

V druhom termináli:

```bash
docker compose -f docker-compose.local.yml exec django python manage.py seed_demo
docker compose -f docker-compose.local.yml exec django python manage.py createsuperuser
```

- Menu (demo stôl): otvorte v admine stôl → stiahnite QR, alebo choďte na
  `/table/<číslo>/<token>/`
- Admin: http://localhost:8000/admin/
- Pokladňa: """"""http://localhost:8000/staff/cashier/orders/""""""
- Kuchyňa: http://localhost:8000/staff/kitchen/orders/

Demo prihlásenia (po `seed_demo`):

| Rola      | E-mail                | Heslo      |
|-----------|-----------------------|------------|
| Admin     | admin@burger.local    | heslo1234  |
| Pokladník | kasa@burger.local     | heslo1234  |
| Kuchyňa   | kuchyna@burger.local  | heslo1234  |

## Produkčné (lokálny server v prevádzke)

```bash
cp .env.example .env          # nastavte produkčné hodnoty
docker compose -f docker-compose.production.yml up -d --build
docker compose -f docker-compose.production.yml exec django python manage.py seed_demo
```

Kontajnery majú `restart: unless-stopped` — po reštarte servera nabehnú automaticky.
Aplikácia beží na porte 80 (Nginx → Daphne). Server by mal mať statickú IP, napr.
`192.168.1.50`, prípadne lokálne meno `menu.local`.

---

## Vývoj bez Dockera

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DJANGO_SETTINGS_MODULE=config.settings.test   # sqlite, bez Postgresu
pytest -q
```

Lokálny beh s Postgresom: nastavte `.env`, `DJANGO_SETTINGS_MODULE=config.settings.local`,
potom `python manage.py migrate && python manage.py runserver`.

## Testy

```bash
pytest -q          # 44+ testov: ceny, stavový automat, services, košík, práva, integrácia
ruff check .
```

---

## Dokumentácia

- [Inštalácia a nasadenie](docs/INSTALL.md)
- [Verejný prístup cez Cloudflare Tunnel](docs/TUNNEL.md) (objednávky z mobilných dát, dáta zostávajú lokálne)
- [Zálohovanie](docs/BACKUP.md) · [Obnova](docs/RESTORE.md)
- Príručky: [Administrátor](docs/MANUAL_ADMIN.md) · [Pokladník](docs/MANUAL_CASHIER.md) · [Kuchyňa](docs/MANUAL_KITCHEN.md)

## Bezpečnosť a kľúčové pravidlá

- Stôl sa určuje len cez serverovú session viazanú na **QR token** — `table_id` sa nedá
  podvrhnúť skrytým poľom.
- Dostupnosť položiek sa overuje na **backende** pri pridaní aj pri odoslaní objednávky.
- Dvojklik nevytvorí duplikát — **idempotency key** na jednu náplň košíka.
- Súbežné úpravy chráni **optimistic locking** (`version`).
- Ceny a názvy sa pri objednávke ukladajú ako **snapshot** — história sa nemení.
- Objednávky sa fyzicky nemažú; rušia sa stavom `CANCELLED`.
- Všetky peniaze sú `Decimal`, časy timezone-aware (`Europe/Bratislava`).
