# ESL Manager UI kontrakt

## Navigácia

Sedem hlavných pohľadov: Prehľad, Cenovky, Produkty, Šablóny, Stanice, Úlohy a Audit. Aktívna položka musí byť viditeľná aj cez `aria-current="page"`; na úzkej obrazovke sa navigácia zbalí do menu.

## Vizuálny systém

IBM Carbon-inšpirovaný offline dizajn:

- farby: Gray 100 `#161616`, Gray 10 `#f4f4f4`, Blue 60 `#0f62fe`, Green `#24a148`, Yellow `#f1c21b`, Red `#da1e28`;
- systémový sans-serif fallback bez CDN;
- 8 px grid, ploché povrchy, nulový radius pre karty/formuláre/tlačidlá;
- 48 px primárne interakčné prvky, viditeľný keyboard focus;
- tabuľky sa na mobile prepínajú na karty alebo horizontálne scrollujú bez orezania akcií.

## Povinné stavy

Každý dátový pohľad má loading, empty, error a loaded stav. Mutácie zobrazujú priebeh a výsledok. Alerty a job status nepoužívajú iba farbu — vždy majú textový štítok.

## Obrazovky

### Prehľad

KPI: počet cenoviek, online/failed, nízka batéria, produkty, otvorené alerty a čakajúce joby. Zobraziť kritické alerty a posledné úlohy.

### Cenovky

Vyhľadávanie podľa MAC/produktu, filtre status/batéria/signál/router, tabuľka inventára, výber viacerých riadkov, detail väzby a akcia vytvoriť update job.

### Produkty

SKU, EAN, názov, cena, jednotka, aktualizácia a priradená cenovka. Create/edit/delete je lokálna operácia s validáciou. CSV export musí byť dostupný bez JavaScript generovania dát.

### Šablóny

Názov, rozmery, typ, mapping type, dynamické polia a počet priradených cenoviek. V prvej verzii read-only voči zariadeniu.

### Stanice

Router ID/IP, stav, heartbeat, frekvencia, verzie a počet tagov.

### Úlohy

Joby a položky so stavmi queued/running/success/failed, percento úspechu, simulované spracovanie a retry iba failed položiek. Live dispatch musí jasne označiť bezpečnostný režim.

### Audit

Čas, typ entity, akcia, identifikátor a bezpečne serializované detaily; read-only, zoradené od najnovšieho.

## Formuláre a bezpečnosť

- Žiadne credentialy ani session cookie v DOM/localStorage.
- Všetky dynamické hodnoty renderovať cez `textContent`, nie `innerHTML`.
- Potvrdenie live zápisu je samostatný krok a UI ho nesmie simulovať ako úspešný bez API odpovede.
- Deštruktívne fyzické DELETE operácie nie sú v UI dostupné.
