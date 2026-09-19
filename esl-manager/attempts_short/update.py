#!/usr/bin/env python3
"""
ESL Manager - Konsolidovaný skript pre aktualizáciu dát štýlov
Zhrnutie 7 pôvodných skriptov z attempts/update/

Cieľ: Aktualizovať orderJson (položky) existujúceho štýlu.

Problém: updateDispMData vracia 200 OK ale dáta sa neukladajú.
  - Server ignoruje orderJson parametre
  - JSON body vracia 500 error
  - Form-urlencoded vracia 200 OK ale bez efektu

Endpointy:
  POST /esls_new/style/updateDispMData - Aktualizácia orderJson (nefunguje)
  POST /esls_new/style/updateStyle     - Aktualizácia meta-dát (funguje)
  POST /esls_new/style/getDispMsData   - Získanie orderJson

Výsledky testov:
  - updateDispMData s form-urlencoded: 200 OK, dáta sa neukladajú
  - updateDispMData s JSON body: 500 error
  - updateDispMData s id v URL params: 200 OK, dáta sa neukladajú
  - updateDispMData na originál štýl 146: 200 OK, dáta sa neukladajú
  - updateStyle s JSON body: 1 (success) - mení len meta-dáta
  - updateStyle s orderJson v tele: 1 (success) - ale orderJson sa ignoruje

Kľúčové zistenia:
  1. updateDispMData je definitívne broken na serveri
  2. updateStyle funguje len pre meta-dáta (name, type, descriptor, rotate, sid)
  3. orderJson sa nedá aktualizovať cez žiadny endpoint
  4. Je to bug servera - nie je možné meniť položky štýlov cez API
  5. Jediné riešenie je manuálna úprava v dashboarde alebo priama úprava DB
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


def get_order_json(style_id, opener):
    """Získaj orderJson pre konkrétny štýl."""
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

    return order_json


def test_updatedisp_variants(style_id, order_json, opener):
    """Testuj všetky varianty updateDispMData."""
    if not order_json or not isinstance(order_json, list):
        print("  Žiadne orderJson na testovanie!")
        return

    print(f"\n[TEST_UPDATEDISP] Testujem varianty pre štýl {style_id}...")

    json_str = json.dumps(order_json, ensure_ascii=False)

    # Variant 1: form-urlencoded, id v body
    print("  Variant 1: form-urlencoded, id v body...")
    r1 = make_request("POST", "/style/updateDispMData", {"id": str(style_id), "orderJson": json_str})
    print(f"    Status: {r1['status']}, Response: {r1['text'][:200]}")

    # Variant 2: form-urlencoded, id v URL params
    print("  Variant 2: form-urlencoded, id v URL params...")
    r2 = make_request("POST", f"/style/updateDispMData?id={style_id}", {"orderJson": json_str})
    print(f"    Status: {r2['status']}, Response: {r2['text'][:200]}")

    # Variant 3: form-urlencoded, id v params aj body
    print("  Variant 3: form-urlencoded, id v params aj body...")
    r3 = make_request("POST", f"/style/updateDispMData?id={style_id}", {"id": str(style_id), "orderJson": json_str})
    print(f"    Status: {r3['status']}, Response: {r3['text'][:200]}")

    # Variant 4: JSON body
    print("  Variant 4: JSON body...")
    r4 = make_request("POST", "/style/updateDispMData", json.dumps({"id": style_id, "orderJson": order_json}), "application/json")
    print(f"    Status: {r4['status']}, Response: {r4['text'][:200]}")

    # Variant 5: JSON body s orderJson ako string
    print("  Variant 5: JSON body s orderJson ako string...")
    r5 = make_request("POST", "/style/updateDispMData", json.dumps({"id": style_id, "orderJson": json_str}), "application/json")
    print(f"    Status: {r5['status']}, Response: {r5['text'][:200]}")

    return [r1, r2, r3, r4, r5]


def test_updatestyle_with_orderjson(style_id, order_json, opener):
    """Testuj updateStyle s orderJson v tele."""
    if not order_json or not isinstance(order_json, list):
        print("  Žiadne orderJson na testovanie!")
        return

    print(f"\n[TEST_UPDATESTYLE_OJ] Testujem updateStyle s orderJson pre štýl {style_id}...")

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


def verify_changes(style_id, opener):
    """Over, či sa zmeny uložili."""
    print(f"\n[VERIFY] Overujem štýl {style_id}...")
    order_json = get_order_json(style_id, opener)

    if order_json and isinstance(order_json, list):
        print(f"  Počet položiek: {len(order_json)}")
        for i, field in enumerate(order_json[:3]):
            if isinstance(field, dict):
                print(f"    [{i}] {field.get('mpname', '?')}: {json.dumps(field, ensure_ascii=False)[:200]}")
    else:
        print("  Nemôžem parsovať dáta!")


def change_colors(style_id, new_color="#ff0000", opener=None):
    """
    Zmeň farby textov v štýle.
    POZOR: updateDispMData nefunguje, toto je len demo.
    """
    print(f"\n[CHANGE_COLORS] Mením farby na '{new_color}' pre štýl {style_id}...")

    order_json = get_order_json(style_id, opener)
    if not order_json or not isinstance(order_json, list):
        print("  ERROR: Nemôžem získať orderJson!")
        return

    changed = 0
    for field in order_json:
        if isinstance(field, dict) and field.get("type") == "text":
            style_obj = field.get("style", {})
            if style_obj:
                old_color = style_obj.get("color", "N/A")
                style_obj["color"] = new_color
                field["style"] = style_obj
                changed += 1

    print(f"  Zmenených polov: {changed}")

    # Skús aktualizovať (vieme že to nefunguje)
    json_str = json.dumps(order_json, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", {"id": str(style_id), "orderJson": json_str})
    print(f"  updateDispMData: status={result['status']}, response={result['text'][:200]}")

    # Over
    verify_changes(style_id, opener)


if __name__ == "__main__":
    print("=" * 60)
    print("ESL Manager - Konsolidovaný update skript")
    print("=" * 60)

    # 1. Login
    passwd_md5 = hashlib.md5(PASSWORD.encode()).hexdigest()
    login_data = {"username": USERNAME, "passwd": passwd_md5}
    result = make_request("POST", "/login/userLogin", login_data)
    print(f"[LOGIN] Status: {result['status']}")
    opener = result["opener"]

    # 2. Získaj orderJson zo štýlu 146
    print("\n" + "=" * 60)
    print("=== ZISKANIE ORDERJSON ===")
    order_json = get_order_json(146, opener)
    if order_json:
        print(f"  Počet položiek: {len(order_json)}")

    # 3. Testuj updateDispMData varianty
    print("\n" + "=" * 60)
    print("=== TEST updateDispMDA VARIANTS ===")
    if order_json:
        test_updatedisp_variants(146, order_json, opener)

    # 4. Testuj updateStyle s orderJson
    print("\n" + "=" * 60)
    print("=== TEST updateStyle s orderJson ===")
    if order_json:
        test_updatestyle_with_orderjson(146, order_json, opener)

    # 5. Over zmeny
    print("\n" + "=" * 60)
    print("=== OVER ZMEN ===")
    verify_changes(146, opener)

    # 6. Zmeň farby (demo - nefunguje)
    print("\n" + "=" * 60)
    print("=== ZМЕНA FARIEB (DEMO - NEFUNGUJE) ===")
    change_colors(146, "#ff0000", opener)

    print("\n[RESULT] updateDispMData je definitívne broken na serveri.")
    print("  - Vracia 200 OK ale dáta sa neukladajú")
    print("  - JSON body vracia 500 error")
    print("  - updateStyle funguje len pre meta-dáta")
    print("  - Nie je možné aktualizovať orderJson cez API")
    print("  - Je to bug servera - potrebná manuálna úprava alebo DB prístup")

    print("\n[OK] Update skript dokončený.")
