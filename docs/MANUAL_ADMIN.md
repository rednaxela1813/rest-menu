# Príručka administrátora

Administrácia: `http://<server>/admin/`

## Prvé spustenie
1. Vytvorte superužívateľa (`createsuperuser`) alebo použite demo `admin@burger.local`.
2. **Prevádzka** → vytvorte/skontrolujte záznam (názov, mena EUR, logo).

## Používatelia a role
**Účty → Používatelia**. Roly: `admin`, `cashier` (pokladňa), `kitchen` (kuchyňa),
`waiter` (čašník). Pridajte kolegom účty s e-mailom a heslom a priraďte rolu.

## Menu
1. **Kategórie** — názov (SK/EN), poradie, voliteľne čas dostupnosti.
2. **Položky menu** — názov, cena, kategória, foto, alergény, modifikátory (inline).
   - `aktívna položka` = vypnutá natrvalo (zmizne z menu).
   - `momentálne dostupná` = dočasne vypredané (zostane viditeľná, nedá sa objednať).
   - Hromadné akcie: *Označiť ako dostupné/nedostupné*.
3. **Skupiny modifikátorov** + **Modifikátory** — extra ingrediencie, odobratie.
   - `SINGLE` = jeden výber (rádio), `MULTIPLE` = viac (checkbox), `min/max`, `povinné`.
4. Pri položke v inline časti priradíte skupiny a môžete prepísať `min/max/povinné` pre danú položku.

## Stoly a QR kódy
**Stoly** — vytvorte stoly (číslo, názov). Pre každý:
- *Stiahnuť PNG* z výpisu,
- alebo PDF všetkých stolov: `/staff/tables/qr.pdf`,
- akcia *Vygenerovať nové QR tokeny* zneplatní staré QR (napr. pri úniku),
- deaktivovaný stôl neprijíma objednávky.

## Objednávky a audit
- **Objednávky** — všetky objednávky, položky, história stavov (len na čítanie, nedajú sa mazať).
- **Denník akcií (AuditLog)** — kto a kedy potvrdil/zamietol/zrušil/zmenil objednávku.

## Zálohy
Viď [BACKUP.md](BACKUP.md). Spúšťajte denne a kópie prenášajte na druhý nosič.
