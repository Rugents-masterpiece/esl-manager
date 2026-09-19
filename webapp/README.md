# ESL Manager Web

Samostatná lokálna webová aplikácia pre inventár, obsluhu a bezpečné riadenie elektronických cenoviek. Backend používa iba Python štandardnú knižnicu a SQLite; statický frontend funguje bez CDN a bez internetového pripojenia.

## Funkcie

- prehľad KPI, alertov a posledných úloh,
- inventár cenoviek, routerov a šablón s filtrami,
- CRUD produktov a väzby produkt ↔ cenovka,
- dávkové aktualizačné úlohy, simulované spracovanie a retry,
- audit udalostí a CSV export produktov,
- read-only synchronizácia s vendor API,
- predvolene zapnutý bezpečný simulačný režim.

## Štruktúra

- `esl_web/` — REST backend, doménová logika, SQLite a vendor adapter
- `static/` — offline HTML/CSS/JavaScript rozhranie
- `tests/` — automatické unit, HTTP a DOM/source testy
- `data/` — runtime SQLite databáza (ignorovaná Gitom)

## Spustenie

Z adresára `webapp/`:

    mkdir -p data
    python3 -c 'from esl_web.server import create_server; create_server("127.0.0.1", 8080, database_path="data/esl.sqlite3", seed=True).serve_forever()'

Potom otvorte:

    http://127.0.0.1:8080/

Server sa štandardne viaže iba na loopback. Pre prístup z LAN zmeňte host na `0.0.0.0` iba v dôveryhodnej sieti a primerane obmedzte firewall.

## Overenie

    python3 -m unittest discover -s tests -v
    python3 -m compileall -q esl_web tests
    node --check static/app.js    # voliteľné, ak je Node.js dostupný

Testy vendor integrácie používajú iba lokálny fake HTTP server; nekontaktujú fyzické ESL zariadenie.

## Vendor synchronizácia a bezpečnosť

Simulačný režim používa bežný štart opísaný vyššie. Live režim používa ignorovaný súbor `data/live-credentials.json` s oprávneniami `0600` a spúšťa sa:

```bash
python3 run_live.py
```

Launcher nenačítava heslo do príkazového riadka, nepridáva demo dáta a zapne procesový write gate iba vtedy, keď JSON obsahuje `"live_writes": true`. Súbor musí obsahovať aj náhodný `api_token` v 64-znakovom URL-safe formáte generovanom zo 48 náhodných bajtov. Pri bindovaní na LAN vyžadujú všetky API mutácie prihlásenie týmto tokenom cez tlačidlo „Prihlásiť pre zápis“. Aplikácia token neukladá a po zatvorení dialógu vyčistí vstupné pole; backend vydá osemhodinovú `HttpOnly`, `SameSite=Strict` session cookie. Synchronizácia načíta všetky strany zoznamu cenoviek.

Konfiguráciu možno naďalej vytvoriť priamo z prostredia cez `ESL_BASE_URL`, voliteľné prihlasovacie údaje/session a timeouty.

Fyzické zápisy sú predvolene zakázané. Endpoint pre live dispatch vyžaduje súčasne:

1. administrátorské nastavenie `ESL_LIVE_WRITES=1`,
2. platnú autentifikovanú write session,
3. presnú potvrdzovaciu frázu v konkrétnej požiadavke,
4. známy stav cenovky pred operáciou a preukázanú zmenu pri následnom read-backu.

Aplikácia neposkytuje ovládanie na fyzické mazanie. Podrobnosti sú v `SECURITY.md`; analyzované zdroje a rozhodnutia sú v nadradenom `ANALYSIS.md`.
