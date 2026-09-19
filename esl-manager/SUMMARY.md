# ESL Manager - Zhrnutie projektu

## Stav projektu (2026-08-03)

### Úspechy
- Knižnica `esl_manager.py` funguje pre čítacie operácie
- Prihlásenie do dashboardu funguje
- Získanie zoznamu štýlov a tagov funguje
- Vytváranie nových štýlov funguje (s bugom 500)
- Aktualizácia metadát štýlov funguje

### Problémy
- Klonovanie štýlu nefunguje (server prepisuje originál)
- `updateDispMData` vracia 200 OK ale dáta sa neukladajú
- Endpoint pre `orderJson` nie je známy
- Browser automatizácia nie je dostupná

### Ďalšie kroky
1. Skúsiť iný formát pre `updateDispMData` (form data vs JSON)
2. Skúsiť nájsť endpoint pre `orderJson` v dynamicky generovaných stránkach
3. Skúsiť browser automation na capture network traffic
4. Skúsiť priamu úpravu databázy (ak je prístupná)

## Štruktúra súborov

- `README.md` - Hlavná dokumentácia
- `docs/api-overview.md` - Dokumentácia API endpointov
- `docs/procedural-guide.md` - Postup pre komunikáciu so serverom
- `attempts/` - Všetky pokusy o komunikáciu
- `js-analysis/` - Analýzy JavaScriptových súborov
- `results/` - Výsledky testov
- `scripts/esl_manager.py` - Fungujúca knižnica
- `scripts/esl_cli.py` - CLI rozhranie
