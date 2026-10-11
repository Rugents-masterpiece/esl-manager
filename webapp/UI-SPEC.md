# ESL Manager UI kontrakt

## Navigácia a kontext

Primárne pohľady sú **Cenovky**, **Šablóny**, **Editor šablón** a **Controllery**. **Audit** je sekundárny pohľad. Aktívny controller sa volí v hlavičke a určuje rozsah vendor inventára. Editor pracuje s lokálnymi návrhmi nezávislými od controllera. Generický produktový a job dashboard nie je súčasťou hlavnej navigácie.

## Vizuálny systém

IBM Carbon-inšpirovaný offline dizajn používa lokálne systémové fonty, Gray 100 `#161616`, Gray 10 `#f4f4f4`, Blue 60 `#0f62fe`, Green `#24a148`, Yellow `#f1c21b` a Red `#da1e28`. Nepoužíva CDN. Interakčné prvky majú najmenej 48 px, viditeľný keyboard focus a responzívne desktopové aj mobilné rozloženie.

## Cenovky

Zoznam obsahuje aj historické nepodporované záznamy, ktoré sú pravdivo označené a nemožno ich upravovať. Detailný drawer zobrazuje controller, RF router, práve jeden z modelov `2.13TFT-BW`, `2.13EPD-BWR`, `2.9EPD-BWR`, kompatibilnú šablónu, zdroj inventára a konfigurácie, telemetriu a testovacie JSON dáta. Escape, backdrop a tlačidlo Zavrieť drawer zatvoria a vrátia focus.

Pridanie cenovky validuje controller, router, model, šablónu, MAC, označenie a JSON. Vytvorí iba lokálny staging cez `/api/tags/staged`; fyzický dispatch nevykonáva. Úprava používa autentifikovaný same-origin endpoint `/api/tags/{id}/configuration`.

## Šablóny

Zobrazujú sa iba rodiny 250 × 132 TFT, 250 × 122 EPD a 296 × 128 EPD. Karta uvádza controller, rozmery, serverové ID a náhľad. Clone dialóg používa štvorpoľový kontrakt `source_controller_id`, `source_template_id`, `target_controller_id`, `target_name`, vyžaduje explicitné potvrdenie a počas požiadavky blokuje opakované odoslanie. Úspech zobrazuje serverové ID a výsledok read-back overenia.

## Editor lokálnych šablón

Editor má plátno displeja, zoznam vrstiev a panel vlastností. Podporuje tri modely a ich palety, text/obdĺžnik/čiaru/obrázok/Code128/QR, presun myšou aj šípkami v pixeloch displeja, duplicitu, poradie vrstiev, undo/redo, fonty prehliadača, ukážkový JSON a dátové pole. Obrázky sa spracúvajú lokálne na vložený PNG; QR má UTF-8 a korekciu L/M/Q/H. Kódy majú reálne generátory, ochranné okraje a celočíselné natívne moduly; neplatný obsah alebo malý rámček blokuje uloženie. Lokálne návrhy sa ukladajú cez `/api/template-drafts` s revíziou a read-back overením. JSON import/export používa vlastný verzovaný formát V1/V2, nie vendor `orderJson`. Neplatné a neuložené úpravy sa nesmú potichu stratiť alebo označiť za uložené. Upozornenie výslovne odlišuje návrh od vendor šablóny a aproximovaný náhľad od fyzického zobrazenia; publikovanie na hardvér zatiaľ nie je implementované.

**Uložené lokálne návrhy** ostávajú SQLite knižnicou. **Šablóny zo zariadenia** majú samostatný controller, živý read-only katalóg `/api/template-draft-sources` a tlačidlo **Načítať kópiu**. Neprípustné modely sú viditeľné a zakázané. Načítanie je neuložený lokálny import, nie zápis na zariadenie ani automatické vytvorenie návrhu. Náhrady fontov, orezanie alebo predpoklad Code128/ECC sa musia zobraziť a potvrdiť pred nahradením otvoreného návrhu; chyba/zrušenie uchová pôvodné úpravy. Až explicitné uloženie pridá kópiu do lokálnej knižnice. V2 dátové väzby zachovávajú presné ploché Unicode kľúče s medzerami; nevykonávajú výrazy a nečítajú zdedené vlastnosti.

## Controllery

Pohľad zobrazuje všetky verejne nakonfigurované controllery a ich rozsah inventára. API `/api/controllers` vracia iba `id`, `name`, `base_url`, `default`; nikdy credentials ani stav klienta.

## Bezpečnosť a prístupnosť

- Dynamické hodnoty sa vkladajú cez `textContent`, nie cez `innerHTML`.
- Session token existuje iba v jednom password inpute. Nezapisuje sa do browser storage a maže sa pri close, cancel, backdrop aj úspechu.
- Mutácie zachovávajú session autentifikáciu a kontrolu Origin na serveri.
- Dialógy majú dostupné názvy, Escape/close/backdrop, focus return a disabled/loading stavy.
- Každý dátový pohľad má loading, empty, error a loaded stav; stav nie je komunikovaný iba farbou.
