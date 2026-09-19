# ESL Manager - Príručka pre používateľa

## Prehľad

Adresár `/home/jamailo/workspace/esl-manager/` obsahuje kompletný projekt pre prácu s ESL serverom.

## Štruktúra

```
esl-manager/
├── README.md              # Hlavná dokumentácia
├── SUMMARY.md             # Zhrnutie projektu
├── USER-GUIDE.md          # Táto príručka
├── docs/
│   ├── api-overview.md    # Dokumentácia všetkých endpointov
│   └── procedural-guide.md # Postup pre komunikáciu so serverom
├── attempts/
│   ├── INDEX.md           # Index všetkých pokusov
│   ├── login/             # 7 skriptov - prihlásenie
│   ├── styles/            # 9 skriptov - práca so štýlmi
│   ├── tags/              # 7 skriptov - práca s tagmi
│   ├── create/            # 5 skriptov - vytváranie nových štýlov
│   ├── update/            # 7 skriptov - aktualizácia dát
│   ├── debug/             # 3 skripty - debugovanie
│   ├── analysis/          # 9 skriptov - analýzy
│   ├── js/                # 10 skriptov - JavaScript analýzy
│   ├── download/          # 1 skript - sťahovanie
│   ├── test/              # 6 skriptov - testy
│   └── misc/              # 6 skriptov - ostatné
├── js-analysis/           # 10 skriptov - analýzy JS súborov
├── results/               # Výsledky testov (prázdny)
└── scripts/
    ├── esl_manager.py     # Hlavná knižnica (fungujúca)
    ├── esl_cli.py         # CLI rozhranie
    └── esl_tester.py      # Testovací skript
```

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

## Ako to používať

### 1. Rýchly štart

```bash
cd /home/jamailo/workspace/esl-manager
python3 scripts/esl_manager.py --help
```

### 2. Prehľad endpointov

Prečítaj si `docs/api-overview.md` pre kompletný prehľad API endpointov.

### 3. Postup pre komunikáciu

Prečítaj si `docs/procedural-guide.md` pre kroky:
1. Prihlásenie
2. Získanie zoznamu štýlov
3. Získanie dát štýlu
4. Vytvorenie nového štýlu
5. Aktualizácia metadát

### 4. Preskúmanie pokusov

Pozri `attempts/INDEX.md` pre prehľad všetkých 69 skriptov.

### 5. Hlavná knižnica

`scripts/esl_manager.py` obsahuje triedu `ESLManager` s metódami:
- `login()` - Prihlásenie
- `get_styles()` - Získanie zoznamu štýlov
- `get_tags()` - Získanie zoznamu tagov
- `get_style_data()` - Získanie dát štýlu
- `create_style()` - Vytvorenie nového štýlu
- `update_style()` - Aktualizácia metadát štýlu

## Ďalšie kroky

1. Skúsiť iný formát pre `updateDispMData` (form data vs JSON)
2. Skúsiť nájsť endpoint pre `orderJson` v dynamicky generovaných stránkach
3. Skúsiť browser automation na capture network traffic
4. Skúsiť priamu úpravu databázy (ak je prístupná)
