#!/usr/bin/env python3
"""
Vytvorí kompletný adresár s dokumentáciou ESL projektu.
"""
import os, shutil, json, textwrap
from datetime import datetime

BASE = "/home/jamailo/workspace/esl-manager"

# Vytvoríme štruktúru
dirs = [
    "docs",
    "attempts/login",
    "attempts/styles",
    "attempts/tags",
    "attempts/create",
    "attempts/update",
    "js-analysis",
    "results",
    "scripts",
]
for d in dirs:
    os.makedirs(f"{BASE}/{d}", exist_ok=True)

# 1. README.md
readme = """# ESL Manager - Dokumentácia projektu

## Prehľad

Tento adresár obsahuje všetky analýzy, pokusy a skripty pre prácu s ESL serverom
(Electronic Shelf Label) na adrese `192.168.16.251`.

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
"""
with open(f"{BASE}/README.md", "w") as f:
    f.write(readme)

# 2. API Overview
api_overview = """# API Overview - ESL Server

## Základné informácie

- **Adresa:** `http://192.168.16.251/esls_new`
- **Prihlásenie:** `POST /esls_new/login/userLogin`
- **Heslo:** MD5 hash
- **Session:** JSESSIONID cookie

## Endpointy

### 1. Login
- **URL:** `POST /esls_new/login/userLogin`
- **Body:** `username=System&password=<md5_hash>&rememberMe=false`
- **Response:** Redirect na `/esls_new/main/index`
- **Cookie:** JSESSIONID sa nastaví automaticky

### 2. getStylesMsg
- **URL:** `POST /esls_new/style/getStylesMsg`
- **Body:** JSON `{"styleType": "all"}`
- **Response:** JSON s polom `styleList` (zoznam všetkých štýlov)
- **Status:** ✅ Funguje

### 3. getTagsMsg
- **URL:** `POST /esls_new/tag/getTagsMsg`
- **Body:** JSON `{}`
- **Response:** JSON s polom `tagList`
- **Status:** ✅ Funguje

### 4. getDispMsData
- **URL:** `POST /esls_new/tag/getDispMsData`
- **Body:** JSON `{"id": <style_id>}`
- **Response:** JSON s dátami štýlu (orderJson, fields, atď.)
- **Status:** ✅ Funguje

### 5. addStyle
- **URL:** `POST /esls_new/style/addStyle`
- **Body:** JSON `{"id": <new_id>, "name": "...", "type": "..."}`
- **Response:** 500 Internal Server Error (NPE bug), ale štýl sa vytvorí
- **Status:** ✅ Funguje (s bugom)

### 6. updateStyle
- **URL:** `POST /esls_new/style/updateStyle`
- **Body:** JSON `{"id": <style_id>, "name": "...", "type": "...", "descriptor": "..."}`
- **Response:** "1" (success)
- **Status:** ✅ Funguje (len meta-dáta, nie orderJson)

### 7. updateDispMData
- **URL:** `POST /esls_new/tag/updateDispMData`
- **Body:** Form data (nie JSON!)
- **Response:** 200 OK
- **Status:** ❌ Dáta sa neukladajú napriek 200 OK

## Kľúčové zistenia

1. Server vracia rôzne formáty: JSON, escaped JSON, HTML, plain strings
2. `addStyle` vracia 500 ale funguje (NPE bug v serveri)
3. `updateStyle` funguje len pre meta-dáta (nie orderJson)
4. `updateDispMData` vracia 200 OK ale dáta sa neukladajú
5. Endpoint pre `orderJson` nie je v statických JS súboroch
"""
with open(f"{BASE}/docs/api-overview.md", "w") as f:
    f.write(api_overview)

# 3. Procedural guide
procedural = """# Postup - Príprava komunikácie s ESL serverom

## Krok 1: Prihlásenie

```python
import urllib.request, http.cookiejar, hashlib

ESL_BASE = "http://192.168.16.251/esls_new"

# Vytvor cookie jar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
password = hashlib.md5(b"vasco123").hexdigest()  # Zmeň na svoje heslo
data = f"username=System&password={password}&rememberMe=false".encode()
req = urllib.request.Request(f"{ESL_BASE}/login/userLogin", data=data)
resp = opener.open(req)
print(f"Login status: {resp.status}")

# Cookie JSESSIONID je teraz v cj
```

## Krok 2: Získanie zoznamu štýlov

```python
import json

# getStylesMsg
body = json.dumps({"styleType": "all"}).encode()
req = urllib.request.Request(f"{ESL_BASE}/style/getStylesMsg", data=body)
req.add_header("Content-Type", "application/json")
resp = opener.open(req)
data = json.loads(resp.read())
styles = data.get("styleList", [])
print(f"Počet štýlov: {len(styles)}")
```

## Krok 3: Získanie dát konkrétnego štýlu

```python
# getDispMsData
body = json.dumps({"id": 146}).encode()
req = urllib.request.Request(f"{ESL_BASE}/tag/getDispMsData", data=body)
req.add_header("Content-Type", "application/json")
resp = opener.open(req)
data = json.loads(resp.read())
print(json.dumps(data, indent=2))
```

## Krok 4: Vytvorenie nového štýlu

```python
# addStyle (vracia 500 ale funguje!)
new_id = 152
body = json.dumps({
    "id": new_id,
    "name": "Novy styl",
    "type": "standard"
}).encode()
req = urllib.request.Request(f"{ESL_BASE}/style/addStyle", data=body)
req.add_header("Content-Type", "application/json")
resp = opener.open(req)
print(f"Status: {resp.status}")  # 500, ale štýl existuje
```

## Krok 5: Aktualizácia metadát štýlu

```python
# updateStyle (funguje pre meta-dáta)
body = json.dumps({
    "id": 146,
    "name": "Upraveny nazov",
    "type": "standard",
    "descriptor": "popis"
}).encode()
req = urllib.request.Request(f"{ESL_BASE}/style/updateStyle", data=body)
req.add_header("Content-Type", "application/json")
resp = opener.open(req)
print(f"Status: {resp.status}, Response: {resp.read()}")  # "1"
```

## Poznámky

- Vždy použi `http.cookiejar.CookieJar()` pre session management
- Heslo sa musí hashovať MD5
- `addStyle` vracia 500 ale štýl sa vytvorí
- `updateStyle` funguje len pre meta-dáta
- `updateDispMData` vracia 200 OK ale dáta sa neukladajú
- Pre `orderJson` nie je známy endpoint
"""
with open(f"{BASE}/docs/procedural-guide.md", "w") as f:
    f.write(procedural)

# 4. Copy JS analysis files
import glob
js_files = glob.glob("/tmp/esl_analyze_*.py") + glob.glob("/tmp/esl_download_*.py")
for f in js_files[:10]:  # Prvych 10
    shutil.copy2(f, f"{BASE}/js-analysis/")

# 5. Copy attempt files
attempts = [
    "/tmp/esl_login_update.py",
    "/tmp/esl_create_and_populate2.py",
    "/tmp/esl_debug_updatedisp.py",
    "/tmp/esl_debug_addstyle.py",
    "/tmp/esl_debug_updatestyle.py",
    "/tmp/esl_verify_updatestyle.py",
    "/tmp/esl_inspect_style.py",
]
for f in attempts:
    if os.path.exists(f):
        shutil.copy2(f, f"{BASE}/attempts/")

# 6. Copy working scripts
shutil.copy2("/home/jamailo/.hermes/scripts/esl_manager.py", f"{BASE}/scripts/")
shutil.copy2("/home/jamailo/.hermes/scripts/esl_cli.py", f"{BASE}/scripts/")

# 7. Summary file
summary = """# ESL Manager - Zhrnutie projektu

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
"""
with open(f"{BASE}/SUMMARY.md", "w") as f:
    f.write(summary)

# 8. Create index for attempts
index_content = """# Index pokusov

## Login
- `esl_login_update.py` - Programmatic login s http.cookiejar

## Styles
- `esl_inspect_style.py` - Inspekcia štruktúry štýlu 146
- `esl_clone_red.py` - Pokus o klonovanie štýlu 146 s červenými farbami
- `esl_change_colors.py` - Priama zmena farieb na štýle 146

## Create
- `esl_create_and_populate.py` - Vytvorenie nového štýlu s dátami z 146
- `esl_create_and_populate2.py` - Aktualizovaná verzia (addStyle s JSON)
- `esl_create_new.py` - Vytvorenie nového štýlu s novým ID

## Update
- `esl_debug_updatedisp.py` - Debug updateDispMData formátu
- `esl_debug_addstyle.py` - Debug addStyle formátu
- `esl_debug_updatestyle.py` - Debug updateStyle formátu
- `esl_verify_updatestyle.py` - Overenie updateStyle zmien
"""
with open(f"{BASE}/attempts/INDEX.md", "w") as f:
    f.write(index_content)

print("✅ Vytvorený kompletný adresár:")
for root, dirs, files in os.walk(BASE):
    level = root.replace(BASE, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in files[:5]:  # Prvych 5 súborov na adresár
        print(f'{subindent}{file}')
    if len(files) > 5:
        print(f'{subindent}... a {len(files) - 5} ďalších')
