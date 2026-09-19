# ESL Manager Web

Samostatná lokálna webová aplikácia pre inventár, obsluhu a bezpečné riadenie elektronických cenoviek.

## Navrhovaná štruktúra

- `esl_web/` — backend, doménová logika, SQLite a vendor adapter
- `static/` — offline HTML/CSS/JavaScript používateľské rozhranie
- `tests/` — automatické unittest testy
- `data/` — runtime SQLite databáza (ignorovaná Gitom)

## Kvalitatívne pravidlá

- Python štandardná knižnica, bez povinného package install.
- TDD: test najprv zlyhá, potom minimálna implementácia.
- Demo/simulation režim je predvolený.
- Žiadne požiadavky na reálne zariadenie v automatických testoch.
