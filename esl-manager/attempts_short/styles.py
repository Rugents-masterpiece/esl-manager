#!/usr/bin/env python3
"""
ESL Manager - Konsolidovaný skript pre prácu so štýlmi
Zhrnutie 9 pôvodných skriptov z attempts/styles/

Cieľ: Získať, analyzovať a aktualizovať štýly na ESL serveri.

Endpointy:
  GET  /esls_new/associate/getStyleMsgs  - Zoznam všetkých štýlov
  POST /esls_new/style/getStyleMsgById   - Detail štýlu podľa ID
  POST /esls_new/style/getDispMsData     - orderJson (položky štýlu)
  POST /esls_new/style/updateStyle       - Aktualizácia metadát štýlu
  GET  /esls_new/style/getStyleData      - Kompletné dáta štýlu
  POST /esls_new/style/addStyle          - Vytvorenie nového štýlu

Štruktúra orderJson (položky štýlu):
  Pole = dict s kľúčmi:
    - id: unikátne ID položky (napr. 1001)
    - mpname: názov položky
    - type: typ položky ("text", "image", "barcode", "price"...)
    - style: dict s formátovaním (color, font, size, align...)
    - x, y: pozícia na displeji
    - width, height: rozmery
    - a, b, c, d: transformácia
    - rotate: rotácia
    - ... ďalšie podľa typu

Výsledky testov:
  - getStyleMsgs vracia zoznam všetkých štýlov s metadátami
  - getDispMsData vracia orderJson (položky štýlu) ako escaped JSON
  - updateStyle s JSON body vracia "1" (success) - mení len meta-dáta
  - updateStyle NEMENÍ orderJson - len name, type, descriptor, rotate, sid
  - addStyle s JSON body vracia 500 ale štýl sa vytvorí (NPE bug)
  - addStyle bez ID v tele vracia 500 ale server pridelí auto-increment ID

Kľúčové zistenia z analýzy style.js:
  1. updateStyle posiela JSON s kľúčmi: name, type, descriptor, rotate, sid
  2. updateStyle nepodporuje orderJson v tele
  3. orderJson sa aktualizuje cez iný endpoint (updateDispMData)
  4. modifyStyle funkcia v JS načíta dáta cez getDispMsData
  5. save štýlu posiela updateStyle + updateDispMData v sekvencii
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


def get_styles(opener):
    """Získaj zoznam všetkých štýlov."""
    print("[GET_STYLES] Načítavam zoznam štýlov...")
    result = make_request("GET", "/associate/getStyleMsgs?currentPage=0&pageSize=200")
    styles = json.loads(result["text_full"])
    datalist = styles.get("datalist", [])
    print(f"  Počet štýlov: {len(datalist)}")
    for s in datalist:
        print(f"    ID {s['id']}: {s.get('name', '?')} (descriptor: {s.get('descriptor', '?')})")
    return datalist


def get_style_data(style_id, opener):
    """Získaj orderJson pre konkrétny štýl."""
    print(f"[GET_DATA] Načítavam dáta pre štýl {style_id}...")
    result = make_request("POST", "/style/getDispMsData", {"id": str(style_id)})
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

    if order_json and isinstance(order_json, list):
        print(f"  Počet položiek: {len(order_json)}")
        for i, field in enumerate(order_json[:3]):
            if isinstance(field, dict):
                print(f"    [{i}] {field.get('mpname', field.get('name', '?'))}: type={field.get('type', '?')}")
        if len(order_json) > 3:
            print(f"    ... a {len(order_json)-3} ďalších")
    else:
        print(f"  Nemôžem parsovať: {raw_text[:200]}")

    return order_json


def update_style_meta(style_id, name, opener):
    """Aktualizuj meta-dáta štýlu (nie orderJson!)."""
    print(f"[UPDATE_META] Aktualizujem meno štýlu {style_id} na '{name}'...")
    update_json = json.dumps({
        "name": name,
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": str(style_id)
    }, ensure_ascii=False)

    result = make_request("POST", "/style/updateStyle", update_json, "application/json")
    print(f"  Status: {result['status']}, Response: {result['text'][:200]}")
    return result


def create_style(name, opener):
    """Vytvor nový štýl cez addStyle."""
    print(f"[CREATE] Vytváram nový štýl '{name}'...")
    create_json = json.dumps({
        "name": name,
        "type": "1",
        "mappingtype": "1"
    }, ensure_ascii=False)

    result = make_request("POST", "/style/addStyle", create_json, "application/json")
    print(f"  Status: {result['status']}, Response: {result['text'][:200]}")

    # Zisti nové ID
    styles = get_styles(opener)
    for s in styles:
        if s.get("name") == name:
            print(f"  Nové ID: {s['id']}")
            return s["id"]

    print("  Štýl nebol nájdený v zozname!")
    return None


def inspect_style_fields(style_id, opener):
    """Detailná analýza štruktúry položiek štýlu."""
    print(f"\n[INSPECT] Detailná analýza štýlu {style_id}...")
    order_json = get_style_data(style_id, opener)

    if not order_json:
        print("  Žiadne dáta!")
        return

    # Analyzuj typy položiek
    type_counts = {}
    for field in order_json:
        if isinstance(field, dict):
            t = field.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\n  Typy položiek:")
    for t, c in sorted(type_counts.items()):
        print(f"    {t}: {c}")

    # Ukáž štruktúru prvej položky každého typu
    print(f"\n  Štruktúra položiek (prvý príklad každého typu):")
    shown = set()
    for field in order_json:
        if isinstance(field, dict):
            t = field.get("type", "unknown")
            if t not in shown:
                shown.add(t)
                print(f"\n    [{t}]")
                print(f"      Kľúče: {list(field.keys())}")
                if "style" in field:
                    print(f"      style.kľúče: {list(field['style'].keys())}")


def test_updatestyle_variants(style_id, order_json, opener):
    """Testuj rôzne varianty updateStyle s orderJson."""
    if not order_json or not isinstance(order_json, list):
        print("  Žiadne orderJson na testovanie!")
        return

    print(f"\n[TEST_UPDATESTYLE] Testujem varianty updateStyle s orderJson...")

    variants = [
        ("orderJson", {"id": style_id, "name": "TEST", "type": "1", "descriptor": "R", "rotate": "0", "sid": str(style_id), "orderJson": order_json}),
        ("fields", {"id": style_id, "name": "TEST", "type": "1", "descriptor": "R", "rotate": "0", "sid": str(style_id), "fields": order_json}),
        ("order_json", {"id": style_id, "name": "TEST", "type": "1", "descriptor": "R", "rotate": "0", "sid": str(style_id), "order_json": order_json}),
        ("data", {"id": style_id, "name": "TEST", "type": "1", "descriptor": "R", "rotate": "0", "sid": str(style_id), "data": order_json}),
        ("dispMData", {"id": style_id, "name": "TEST", "type": "1", "descriptor": "R", "rotate": "0", "sid": str(style_id), "dispMData": order_json}),
        ("styleData", {"id": style_id, "name": "TEST", "type": "1", "descriptor": "R", "rotate": "0", "sid": str(style_id), "styleData": order_json}),
        ("styleJson", {"id": style_id, "name": "TEST", "type": "1", "descriptor": "R", "rotate": "0", "sid": str(style_id), "styleJson": order_json}),
        ("json", {"id": style_id, "name": "TEST", "type": "1", "descriptor": "R", "rotate": "0", "sid": str(style_id), "json": order_json}),
    ]

    for name, data in variants:
        json_body = json.dumps(data, ensure_ascii=False)
        result = make_request("POST", "/style/updateStyle", json_body, "application/json")
        print(f"  {name:12s}: status={result['status']}, response={result['text'][:50]}")


if __name__ == "__main__":
    print("=" * 60)
    print("ESL Manager - Konsolidovaný štýly skript")
    print("=" * 60)

    # 1. Login
    passwd_md5 = hashlib.md5(PASSWORD.encode()).hexdigest()
    login_data = {"username": USERNAME, "passwd": passwd_md5}
    result = make_request("POST", "/login/userLogin", login_data)
    print(f"[LOGIN] Status: {result['status']}")
    opener = result["opener"]

    # 2. Získaj zoznam štýlov
    styles = get_styles(opener)

    # 3. Analyzuj štýl 146
    print("\n" + "=" * 60)
    print("=== ANALÝZA ŠTÝLU 146 ===")
    order_json = get_style_data(146, opener)

    # 4. Detailná štruktúra
    inspect_style_fields(146, opener)

    # 5. Testuj varianty updateStyle
    test_updatestyle_variants(146, order_json, opener)

    # 6. Testuj vytvorenie nového štýlu
    print("\n" + "=" * 60)
    print("=== TEST VYTvoreNIA NOVÉHO ŠTÝLU ===")
    new_id = create_style("Rudo_Test_Style", opener)

    if new_id:
        # Skús aktualizovať orderJson nového štýlu
        print(f"\n[UPDATE] Skúšam aktualizovať orderJson pre štýl {new_id}...")
        if order_json:
            new_order = copy.deepcopy(order_json)
            new_ids = [5000 + i for i in range(len(new_order))]
            for i, field in enumerate(new_order):
                if isinstance(field, dict):
                    field["id"] = new_ids[i]
                    field["name"] = f"test_{i+1}"

            json_str = json.dumps(new_order, ensure_ascii=False)
            update_result = make_request("POST", "/style/updateDispMData", {"id": str(new_id), "orderJson": json_str})
            print(f"  updateDispMData: status={update_result['status']}, response={update_result['text'][:200]}")

            # Over
            print(f"\n[VERIFY] Overujem štýl {new_id}...")
            verify_data = get_style_data(new_id, opener)
            if verify_data:
                print(f"  Počet položiek po update: {len(verify_data)}")
            else:
                print("  Nemôžem parsovať dáta po update!")

    print("\n[OK] Štýly skript dokončený.")
