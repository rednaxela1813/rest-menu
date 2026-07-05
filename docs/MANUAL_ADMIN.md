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
3. **Skupiny modifikátorov** + **Modifikátory** — príloha, omáčka, nápoj, extra/odobratie.
   - `SINGLE` = jeden výber (rádio), `MULTIPLE` = viac (checkbox), `min/max`, `povinné`.
   - `predvolene skryté` = skupina sa v objednávke zobrazí ako zbalený panel (klikom sa rozbalí).
   - **Podkategórie (vnorené skupiny):** vyplňte `nadradená skupina` a skupina sa stane podkategóriou.
     Napr. kontajner **Nápoj** (bez vlastných možností) → podkategórie **Pivo / Víno / Nealko**,
     každá s vlastnými možnosťami a vlastným `min/max`. Podporuje sa **jedna úroveň** vnorenia.
     Kontajner: `max = 0` znamená bez spoločného limitu (možno vybrať napr. pivo aj nealko naraz);
     `max = 1` obmedzí výber na jeden nápoj spolu.
4. Pri položke v inline časti priradíte **len skupiny najvyššej úrovne** (kontajner alebo bežnú
   skupinu) a môžete prepísať `min/max/povinné`. Podkategórie sa priradia automaticky cez strom.

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
