# ESL Manager - attempts_short

## Prehľad

Tento adresár obsahuje zjednodušené, konsolidované verzie všetkých pokusov z `../attempts/`.
Každý podadresár bol zlúčený do jedného súboru pre lepšiu prehľadnosť.

## Súbory

| Súbor | Pôvodný počet skriptov | Popis |
|-------|----------------------|-------|
| `login.py` | 7 | Prihlásenie, analýza login stránky, session management |
| `styles.py` | 9 | Získanie, analýza, aktualizácia štýlov |
| `tags.py` | 6 | Získanie, analýza, aktualizácia tagov |
| `create.py` | 5 | Vytváranie nových štýlov, clone workaround |
| `update.py` | 7 | Aktualizácia orderJson, testovanie variantov |
| `debug.py` | 3 | Debugovanie request/response formátov |
| `analysis.py` | 9 | Analýza HTML a JS súborov z dashboardu |
| `js.py` | 10 | Stiahnutie a analýza JS súborov |
| `test.py` | 6 | Komplexné testovanie všetkých endpointov |
| `misc.py` | 6 | CLI rozhranie, HTML dump, inline scripts |

## Ako používať

```bash
# Prihlásenie a overenie session
python3 login.py

# Získanie zoznamu štýlov a analýza
python3 styles.py

# Získanie zoznamu tagov
python3 tags.py

# Vytvorenie nového štýlu (clone workaround)
python3 create.py

# Aktualizácia orderJson (demo - nefunguje)
python3 update.py

# Debugovanie endpointov
python3 debug.py

# Analýza HTML a JS súborov
python3 analysis.py

# Stiahnutie a analýza JS súborov
python3 js.py

# Komplexné testovanie
python3 test.py

# CLI rozhranie
python3 misc.py --help
```

## Kľúčové zistenia

1. **updateDispMData je definitívne broken** - vracia 200 OK ale dáta sa neukladajú
2. **updateStyle funguje len pre meta-dáta** - name, type, descriptor, rotate, sid
3. **addStyle funguje napriek 500 erroru** - NPE bug v serveri
4. **orderJson endpoint nie je v žiadnom statickom JS súbore** - dynamicky generovaný
5. **app.js je len Bootstrap** - žiadna ESL logika
6. **style.js a tag.js obsahujú API logiku** - modifyStyle, updateStyle, tag/update
7. **Server má konzistentný response format** - escaped JSON, clean JSON, HTML, plain strings

## Ďalšie kroky

- Manuálna úprava štýlov cez dashboard
- Priamy prístup k databáze (ak je prístupná)
- Návrh workaroudu pre klonovanie štýlov
- Oprava bugu na strane servera (ak je možná)
