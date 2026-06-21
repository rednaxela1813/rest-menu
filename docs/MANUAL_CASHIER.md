# Príručka pokladníka

Otvorte `http://<server>/с` a prihláste sa.

## Kanban doska
Stĺpce: **Nové → Potvrdené → Pripravuje sa → Pripravené → Vydané**.

- Nová objednávka sa zobrazí **automaticky**, s **rámčekom/animáciou** a **zvukom**.
- Vo vkladke prehliadača sa zmení názov („🔔 Nová objednávka!“).
- Ak vypadne WebSocket, doska sa aj tak obnoví každých ~10 s (polling).

> Zvuk sa v prehliadači spustí až po prvom kliknutí na stránku (ochrana proti autoplay).

## Spracovanie objednávky
Kliknite na kartu → detail (číslo, stôl, čas, zdroj, položky, modifikátory, poznámka, suma).

Akcie:
- **Potvrdiť** → objednávka prejde na kuchyňu (NEW → CONFIRMED).
- **Zamietnuť** → NEW → REJECTED.
- **Zrušiť** → kým nie je vydaná.
- **Vydať** → keď je *Pripravené* (READY → SERVED).

História stavov je v spodnej časti detailu.

## Pravidlá
- Stav sa nedá preskočiť (napr. nemožno „Vydať“ novú objednávku) — systém to nedovolí.
- Ak objednávku medzitým zmenil kolega, dostanete hlášku „načítajte ju znova“ (ochrana
  proti súbežnej úprave). Obnovte stránku a akciu zopakujte.
