# ESL Manager - Dokumentácia projektu

## Prehľad

Tento adresár obsahuje všetky analýzy, pokusy a skripty pre prácu s ESL serverom (Electronic Shelf Label) na adrese `192.168.16.251`.

## Štruktúra

- `docs/` - Dokumentácia API, endpointov, analýzy
- `attempts/` - Všetky pokusy o komunikáciu so serverom (podľa kategórií)
- `js-analysis/` - Analýzy JavaScriptových súborov z dashboardu
- `results/` - Výsledky testov a overení
- `scripts/` - Fungujúce skripty na použitie

## Čo sa podarilo

- ✅ Prihlásenie do dashboardu (`login/userLogin`)
- ✅ Získanie zoznamu štýlov (`getStylesMsg`)
- ✅ Získanie zoznamu tagov (`getTagsMsg`)
- ✅ Získanie dát štýlu (`getDispMsData`)
- ✅ Vytvorenie nového štýlu (`addStyle` - JSON body, vracia 500 ale funguje)
- ✅ Aktualizácia metadát štýlu (`updateStyle` - JSON body, vracia "1")
- ✅ Testovanie `updateDispMData` (vracia 200 OK, ale dáta sa neukladajú)

## Čo sa nepodarilo

- ❌ Klonovanie štýlu (server vracia rovnaké ID, prepisuje originál)
- ❌ `updateDispMData` - dáta sa neukladajú napriek 200 OK
- ❌ Nájdenie endpointu pre aktualizáciu `orderJson` (nie je v statických JS súboroch)
- ❌ Browser automatizácia (nie je dostupná)

## Rýchly štart

1. Prečítaj `docs/api-overview.md` pre pochopenie endpointov
2. Pozri `attempts/` pre konkrétne pokusy a výsledky
3. Použi `scripts/esl_manager.py` ako knižnicu pre prácu s ESL serverom
