#!/usr/bin/env python3
"""
ESL Manager - Konsolidovaný skript pre vytváranie nových štýlov
Zhrnutie 5 pôvodných skriptov z attempts/create/

Cieľ: Vytvoriť nový štýl na základe existujúceho (klonovanie).

Problém: Server nemá endpoint na klonovanie štýlov.
  - clone_style() vracia rovnaké ID (prepíše originál)
  - updateStyle mení len meta-dáta, nie orderJson
  - updateDispMData vracia 200 OK ale dáta sa neukladajú

Workaround:
  1. Vytvor nový štýl cez addStyle (JSON body, vracia 500 ale funguje)
  2. Zisti nové ID zo zoznamu štýlov
  3. Skús aktualizovať orderJson cez updateDispMData

Endpointy:
  POST /esls_new/style/addStyle       - Vytvorenie nového štýlu (JSON body)
  POST /esls_new/style/getStylesData  - Zoznam štýlov s ID
  POST /esls_new/style/updateDispMData - Aktualizácia orderJson (nefunguje)

Výsledky testov:
  - addStyle s JSON body vracia 500 ale štýl sa vytvorí (NPE bug v serveri)
  - addStyle bez ID v tele -> server pridelí auto-increment ID
  - addStyle s id=9999 v tele -> server ignoruje ID a pridelí vlastné
  - getStylesData vracia nameList a idxList (nie JSON array)
  - updateDispMData vracia 200 OK ale dáta sa neukladajú
  - updateDispMData s JSON body vracia 500

Kľúčové zistenia:
  1. addStyle funguje aj napriek 500 erroru (NPE v serveri)
  2. Server vracia 500 lebo sa snaží aktualizovať orderJson na prázdny štýl
  3. orderJson sa musí aktualizovať cez updateDispMData
  4. updateDispMData nefunguje - server ignoruje dáta
  5. Je to bug servera - nie je možné klonovať štýl cez API
"""

import json
import urllib.request
import urllib.parse
import hashlib
import http.cookiejar
import copy

ESL_BASE = "http://192.168.16.251/esls_new"
USERNAME = "admin"
PASSWORD = "admin"


def make_request(method, path, data=None, content_type="application/x-www-form-urlencoded; charset=UTF-8"):
    """Urobi request a vrati detailne info."""
    url = f"{ESL_BASE}{path}"
    body = None
    if data:
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
        elif isinstance(data, str):
            body = data.encode("utf-8")
        elif isinstance(data, bytes):
            body = data

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", content_type)
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Accept", "*/*")
    req.add_header("Origin", ESL_BASE)
    req.add_header("Referer", f"{ESL_BASE}/")

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    try:
        with opener.open(req, timeout=30) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace").strip()
            return {
                "status": resp.status,
                "text": text[:500],
                "text_full": text,
                "opener": opener,
            }
    except urllib.error.HTTPError as e:
        raw = e.read()
        text = raw.decode("utf-8", errors="replace").strip()
        return {
            "status": e.code,
            "text": text[:500],
            "text_full": text,
            "error": True,
            "opener": opener,
        }


def parse_response(raw):
    """Parse response - handle escaped JSON, clean JSON, etc."""
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith('"') and text.endswith('"'):
        inner = text[1:-1].replace('\\"', '"')
        return json.loads(inner)
    return json.loads(text)


def get_all_styles(opener):
    """Získaj zoznam všetkých štýlov vrátane ID."""
    print("[GET_STYLES] Načítavam zoznam štýlov...")
    result = make_request("GET", "/associate/getStyleMsgs?currentPage=0&pageSize=200")
    styles = json.loads(result["text_full"])
    datalist = styles.get("datalist", [])
    print(f"  Počet štýlov: {len(datalist)}")

    # Nájdi max ID
    max_id = 0
    for s in datalist:
        sid = s.get("id", 0)
        if sid > max_id:
            max_id = sid
    print(f"  Max ID: {max_id}")

    return datalist, max_id


def create_style_via_addstyle(name, opener):
    """Vytvor nový štýl cez addStyle endpoint."""
    print(f"\n[CREATE] Vytváram štýl '{name}' cez addStyle...")

    # Variant 1: JSON body bez ID
    create_json = json.dumps({
        "name": name,
        "type": "1",
        "mappingtype": "1"
    }, ensure_ascii=False)

    result = make_request("POST", "/style/addStyle", create_json, "application/json")
    print(f"  Variant 1 (bez ID): status={result['status']}, response={result['text'][:200]}")

    # Variant 2: JSON body s ID
    create_json2 = json.dumps({
        "id": 9999,
        "name": name + "_with_id",
        "type": "1",
        "mappingtype": "1"
    }, ensure_ascii=False)

    result2 = make_request("POST", "/style/addStyle", create_json2, "application/json")
    print(f"  Variant 2 (s id=9999): status={result2['status']}, response={result2['text'][:200]}")

    # Variant 3: form-urlencoded s data=kľúč
    form_data = {"data": create_json}
    result3 = make_request("POST", "/style/addStyle", form_data)
    print(f"  Variant 3 (form-urlencoded): status={result3['status']}, response={result3['text'][:200]}")

    # Variant 4: form-urlencoded s id + data
    form_data2 = {"id": "9997", "data": create_json}
    result4 = make_request("POST", "/style/addStyle", form_data2)
    print(f"  Variant 4 (form + id+data): status={result4['status']}, response={result4['text'][:200]}")

    return [result, result2, result3, result4]


def find_new_style(styles, name):
    """Nájdi nový štýl v zozname."""
    for s in styles:
        if s.get("name") == name:
            return s["id"]
    return None


def clone_style_workaround(source_id, new_name, opener):
    """
    Workaround pre klonovanie štýlu:
    1. Získaj orderJson zo zdrojového štýlu
    2. Vytvor nový štýl cez addStyle
    3. Zisti nové ID
    4. Skús aktualizovať orderJson cez updateDispMData
    """
    print(f"\n[CLONE_WORKAROUND] Klonujem štýl {source_id} -> '{new_name}'...")

    # 1. Získaj orderJson zo zdrojového štýlu
    print("  [1/4] Načítam orderJson zo zdrojového štýlu...")
    result = make_request("POST", "/style/getDispMsData", {"id": str(source_id)})
    raw_text = result["text_full"]

    order_json = None
    if raw_text.startswith('"') and raw_text.endswith('"'):
        inner = raw_text[1:-1].replace('\\"', '"')
        try:
            order_json = json.loads(inner)
        except:
            pass
    elif raw_text.startswith('['):
        try:
            order_json = json.loads(raw_text)
        except:
            pass

    if not order_json or not isinstance(order_json, list):
        print("  ERROR: Nemôžem parsovať orderJson!")
        return None

    print(f"    Počet položiek: {len(order_json)}")

    # 2. Vytvor nový štýl
    print("  [2/4] Vytváram nový štýl cez addStyle...")
    create_json = json.dumps({
        "name": new_name,
        "type": "1",
        "mappingtype": "1"
    }, ensure_ascii=False)

    result = make_request("POST", "/style/addStyle", create_json, "application/json")
    print(f"    Status: {result['status']}, Response: {result['text'][:200]}")

    # 3. Zisti nové ID
    print("  [3/4] Hľadám nové ID...")
    styles, _ = get_all_styles(opener)
    new_id = find_new_style(styles, new_name)

    if not new_id:
        print("    ERROR: Nový štýl nebol nájdený!")
        return None

    print(f"    Nové ID: {new_id}")

    # 4. Skús aktualizovať orderJson
    print("  [4/4] Skúšam aktualizovať orderJson cez updateDispMData...")

    # Uprav ID položiek
    new_order = copy.deepcopy(order_json)
    new_field_ids = [5000 + i for i in range(len(new_order))]
    for i, field in enumerate(new_order):
        if isinstance(field, dict):
            field["id"] = new_field_ids[i]
            field["name"] = f"cloned_{i+1}"

    json_str = json.dumps(new_order, ensure_ascii=False)
    update_result = make_request("POST", "/style/updateDispMData", {
        "id": str(new_id),
        "orderJson": json_str
    })

    print(f"    Status: {update_result['status']}, Response: {update_result['text'][:200]}")

    # Over
    print(f"\n  [VERIFY] Overujem nový štýl {new_id}...")
    verify = make_request("POST", "/style/getDispMsData", {"id": str(new_id)})
    verify_raw = verify["text_full"]

    verify_data = None
    if verify_raw.startswith('"') and verify_raw.endswith('"'):
        inner = verify_raw[1:-1].replace('\\"', '"')
        try:
            verify_data = json.loads(inner)
        except:
            pass
    elif verify_raw.startswith('['):
        try:
            verify_data = json.loads(verify_raw)
        except:
            pass

    if verify_data and isinstance(verify_data, list):
        print(f"    Počet položiek po update: {len(verify_data)}")
        if len(verify_data) > 0:
            print(f"    Prvé pole ID: {verify_data[0].get('id', '?')}")
    else:
        print(f"    ERROR: Nemôžem parsovať dáta po update!")
        print(f"    Response: {verify_raw[:300]}")

    return new_id


if __name__ == "__main__":
    print("=" * 60)
    print("ESL Manager - Konsolidovaný create skript")
    print("=" * 60)

    # 1. Login
    passwd_md5 = hashlib.md5(PASSWORD.encode()).hexdigest()
    login_data = {"username": USERNAME, "passwd": passwd_md5}
    result = make_request("POST", "/login/userLogin", login_data)
    print(f"[LOGIN] Status: {result['status']}")
    opener = result["opener"]

    # 2. Testuj addStyle varianty
    print("\n" + "=" * 60)
    print("=== TEST addStyle VARIANTY ===")
    results = create_style_via_addstyle("Test_Style_1", opener)

    # 3. Workaround pre klonovanie
    print("\n" + "=" * 60)
    print("=== CLONE WORKAROUND ===")
    new_id = clone_style_workaround(146, "Klon_146_Test", opener)

    if new_id:
        print(f"\n[RESULT] Nový štýl vytvorený s ID {new_id}")
        print("  POZOR: updateDispMData nefunguje - dáta sa neukladajú")
        print("  Je to bug servera - nie je možné klonovať štýl cez API")
    else:
        print("\n[RESULT] Klonovanie zlyhalo")

    print("\n[OK] Create skript dokončený.")
