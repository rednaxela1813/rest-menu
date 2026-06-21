# Verejný prístup cez Cloudflare Tunnel (variant 2)

Cieľ: hosť otvorí menu zo **svojich mobilných dát** (bez pripojenia na Wi-Fi
prevádzky), pričom **server a dáta zostávajú lokálne** v reštaurácii. Cloudflare
Tunnel vytvorí odchádzajúce spojenie z lokálneho servera do siete Cloudflare a
sprístupní appku na verejnej HTTPS adrese. **Na routeri sa neotvára žiadny port.**

```
Telefón hosťa (LTE/5G) ──HTTPS──> Cloudflare edge ──tunel──> cloudflared
                                                                  │ (lokálna sieť)
                                                              nginx → django → postgres
```

---

## Možnosť A — pomenovaný tunel s vlastnou doménou (odporúčané, produkcia)

Potrebujete: účet Cloudflare (zdarma) a doménu pridanú do Cloudflare.

### 1. Vytvorte tunel
1. Cloudflare dashboard → **Zero Trust** → **Networks → Tunnels** → **Create a tunnel**.
2. Typ **Cloudflared**, pomenujte ho napr. `burger-menu`.
3. V kroku „Install connector“ skopírujte **token** (dlhý reťazec za `--token`).

### 2. Nasmerujte verejné meno na nginx
V tuneli → **Public Hostname** → **Add a public hostname**:
- **Subdomain/Domain**: napr. `menu.vasa-restauracia.sk`
- **Service**: **HTTP** → URL `nginx:80`

(Cloudflare ukončuje TLS, k nginx ide po HTTP cez tunel. WebSocket je podporovaný automaticky.)

### 3. Doplňte `.env`
```env
CLOUDFLARE_TUNNEL_TOKEN=<token z kroku 1>
PUBLIC_BASE_URL=https://menu.vasa-restauracia.sk
DJANGO_ALLOWED_HOSTS=menu.vasa-restauracia.sk,192.168.1.50,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://menu.vasa-restauracia.sk
DJANGO_SECURE_COOKIES=True
```

### 4. Spustite produkčný stack + tunel
```bash
docker compose -f docker-compose.production.yml -f docker-compose.tunnel.yml up -d --build
```

### 5. Vygenerujte QR znova
QR kódy musia obsahovať novú HTTPS adresu. V admine (Stoly) stiahnite PNG/PDF —
URL bude `https://menu.vasa-restauracia.sk/table/<číslo>/<token>/`.

### Overenie
```bash
curl -I https://menu.vasa-restauracia.sk/health/        # 200
docker compose -f docker-compose.production.yml -f docker-compose.tunnel.yml logs cloudflared | tail
```

---

## Možnosť B — rýchly tunel na otestovanie (bez domény, dočasné)

Dá vám náhodnú adresu `https://<nieco>.trycloudflare.com`. Mení sa pri každom
spustení — vhodné len na test.

1. Spustite lokálny dev stack:
   ```bash
   docker compose -f docker-compose.local.yml up -d
   ```
2. Spustite rýchly tunel pripojený na rovnakú sieť (mieri na django:8000):
   ```bash
   docker run --rm --network burger_menu_default cloudflare/cloudflared:latest \
       tunnel --url http://django:8000
   ```
   V logu sa objaví riadok s adresou `https://xxxx.trycloudflare.com`.
3. Do `.env` dočasne pridajte (a `docker compose ... up -d django` na reštart):
   ```env
   DJANGO_ALLOWED_HOSTS=.trycloudflare.com,192.168.1.112,localhost,127.0.0.1
   DJANGO_CSRF_TRUSTED_ORIGINS=https://*.trycloudflare.com
   PUBLIC_BASE_URL=https://xxxx.trycloudflare.com
   ```
4. Vygenerujte QR a naskenujte telefónom na mobilných dátach.

> Pre dev (`docker-compose.local.yml`) Django beží so `config.settings.local`,
> kde `ALLOWED_HOSTS=['*']`. CSRF cez HTTPS ale vyžaduje doménu v
> `DJANGO_CSRF_TRUSTED_ORIGINS` — preto ju doplňte podľa kroku 3.

---

## Poznámky a bezpečnosť

- **Závislosť na internete**: variant 2 funguje len keď má prevádzka funkčný
  internet (tunel je odchádzajúce spojenie). Pri výpadku internetu objednávky
  cez verejnú adresu nefungujú; personál (pokladňa/kuchyňa) môže pracovať ďalej
  v lokálnej sieti na `http://<IP>:8000` alebo `http://<IP>/`.
- **Dáta zostávajú lokálne** — Cloudflare len prepája spojenie, databáza je na
  vašom serveri.
- Po zmene `PUBLIC_BASE_URL` **vždy vygenerujte QR kódy nanovo**.
- Voliteľne pridajte v Cloudflare Zero Trust **rate limiting** alebo **WAF**
  pravidlá na `/orders/` proti zneužitiu.
- `cloudflared` má `restart: unless-stopped`, takže po reštarte servera tunel
  nabehne automaticky spolu s ostatnými kontajnermi.
