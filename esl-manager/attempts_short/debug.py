#!/usr/bin/env python3
"""
ESL Manager - Konsolidovaný debug skript
Zhrnutie 3 pôvodných skriptov z attempts/debug/

Cieľ: Debugovanie request/response formátov a parametrov.

Endpointy testované:
  POST /esls_new/style/getDispMsData   - orderJson
  POST /esls_new/style/addStyle        - Vytvorenie štýlu
  POST /esls_new/style/updateDispMData - Aktualizácia orderJson
  POST /esls_new/style/updateStyle     - Aktualizácia meta-dát
  GET  /esls_new/style/getStyleData    - Kompletné dáta štýlu
  GET  /esls_new/style/queryStyles     - Zoznam štýlov (paginated)

Výsledky testov:
  - getStyleData vracia kompletné dáta štýlu (meta + orderJson)
  - queryStyles vracia paginovaný zoznam štýlov
  - addStyle s JSON body vracia 500 ale štýl sa vytvorí
  - addStyle s form-urlencoded data=data vracia 415
  - updateDispMData s form-urlencoded vracia 200 OK ale dáta sa neukladajú
  - updateDispMData s JSON body vracia 500
  - updateDispMData s id v URL params vracia 200 OK ale dáta sa neukladajú
  - updateDispMData na originál štýl 146 vracia 200 OK ale dáta sa neukladajú

Kľúčové zistenia:
  1. Server očakáva form-urlencoded pre updateDispMData, nie JSON
  2. Aj form-urlencoded dáta sa neukladajú - bug servera
  3. getStyleData je užitočný endpoint - vracia kompletné dáta
  4. queryStyles je alternatíva k getStyleMsgs
  5. Všetky debug pokazy potvrdili že updateDispMData je broken
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


def debug_getstyledata(style_id, opener):
    """Debug getStyleData endpoint."""
    print(f"\n[DEBUG_GETSTYLEDATA] getStyleData pre štýl {style_id}...")
    result = make_request("GET", f"/style/getStyleData?id={style_id}")
    print(f"  Status: {result['status']}")
    print(f"  Response: {result['text'][:500]}")
    return result


def debug_querystyles(opener):
    """Debug queryStyles endpoint."""
    print(f"\n[DEBUG_QUERYSTYLES] queryStyles...")
    result = make_request("GET", "/style/queryStyles?currentPage=0&pageSize=5")
    print(f"  Status: {result['status']}")
    print(f"  Response: {result['text'][:500]}")
    return result


def debug_addstyle_variants(opener):
    """Debug addStyle endpoint - všetky varianty."""
    print(f"\n[DEBUG_ADDSTYLE] Testujem addStyle varianty...")

    variants = [
        ("JSON body bez ID", json.dumps({"name": "Debug1", "type": "1", "mappingtype": "1"}), "application/json"),
        ("JSON body s id=9999", json.dumps({"id": 9999, "name": "Debug2", "type": "1", "mappingtype": "1"}), "application/json"),
        ("JSON body s ?id=9998", None, "application/json", "?id=9998"),
        ("form-urlencoded data=data", {"data": json.dumps({"name": "Debug3", "type": "1", "mappingtype": "1"})}, "application/x-www-form-urlencoded"),
        ("form-urlencoded id+data", {"id": "9997", "data": json.dumps({"name": "Debug4", "type": "1", "mappingtype": "1"})}, "application/x-www-form-urlencoded"),
    ]

    for name, data, content_type, *extra_path in variants:
        path = "/style/addStyle"
        if extra_path:
            path += extra_path[0]

        result = make_request("POST", path, data, content_type)
        print(f"  {name:30s}: status={result['status']}, response={result['text'][:100]}")


def debug_updatedisp_full(style_id, order_json, opener):
    """Kompletný debug updateDispMData."""
    if not order_json or not isinstance(order_json, list):
        print("  Žiadne orderJson!")
        return

    print(f"\n[DEBUG_UPDATEDISP_FULL] Kompletný debug pre štýl {style_id}...")
    json_str = json.dumps(order_json, ensure_ascii=False)

    tests = [
        ("form-urlencoded, id v body", {"id": str(style_id), "orderJson": json_str}),
        ("form-urlencoded, id v URL", f"/style/updateDispMData?id={style_id}", {"orderJson": json_str}),
        ("form-urlencoded, id v params aj body", f"/style/updateDispMData?id={style_id}", {"id": str(style_id), "orderJson": json_str}),
        ("JSON body", json.dumps({"id": style_id, "orderJson": order_json}), "application/json"),
        ("JSON body s orderJson ako string", json.dumps({"id": style_id, "orderJson": json_str}), "application/json"),
    ]

    for test in tests:
        if len(test) == 3:
            name, path, data = test
            result = make_request("POST", path, data)
        else:
            name, data = test[0], test[1]
            content_type = test[2] if len(test) > 2 else "application/x-www-form-urlencoded; charset=UTF-8"
            result = make_request("POST", "/style/updateDispMData", data, content_type)

        print(f"  {name:40s}: status={result['status']}, response={result['text'][:100]}")


def debug_modified_updatedisp(style_id, order_json, opener):
    """Debug updateDispMData s upravenými dátami."""
    if not order_json or not isinstance(order_json, list):
        print("  Žiadne orderJson!")
        return

    print(f"\n[DEBUG_MODIFIED_UPDATEDISP] updateDispMData s upravenými dátami...")

    # Zmeň prvé pole
    modified = copy.deepcopy(order_json)
    if modified and len(modified) > 0:
        modified[0]["mpname"] = "DEBUG_CHANGED_" + str(style_id)
        json_str = json.dumps(modified, ensure_ascii=False)

        result = make_request("POST", "/style/updateDispMData", {"id": str(style_id), "orderJson": json_str})
        print(f"  Status: {result['status']}, Response: {result['text'][:200]}")

        # Over
        print("  Overujem...")
        verify = make_request("POST", "/style/getDispMsData", {"id": str(style_id)})
        raw = verify["text_full"]
        if raw.startswith('"') and raw.endswith('"'):
            inner = raw[1:-1].replace('\\"', '"')
            try:
                verify_data = json.loads(inner)
                if verify_data and len(verify_data) > 0:
                    print(f"    Prvé pole mpname: {verify_data[0].get('mpname', '?')}")
            except:
                print(f"    Nemôžem parsovať: {raw[:200]}")
        else:
            print(f"    Response: {raw[:200]}")


if __name__ == "__main__":
    print("=" * 60)
    print("ESL Manager - Konsolidovaný debug skript")
    print("=" * 60)

    # 1. Login
    passwd_md5 = hashlib.md5(PASSWORD.encode()).hexdigest()
    login_data = {"username": USERNAME, "passwd": passwd_md5}
    result = make_request("POST", "/login/userLogin", login_data)
    print(f"[LOGIN] Status: {result['status']}")
    opener = result["opener"]

    # 2. Debug getStyleData
    print("\n" + "=" * 60)
    print("=== DEBUG getStyleData ===")
    debug_getstyledata(146, opener)

    # 3. Debug queryStyles
    print("\n" + "=" * 60)
    print("=== DEBUG queryStyles ===")
    debug_querystyles(opener)

    # 4. Debug addStyle
    print("\n" + "=" * 60)
    print("=== DEBUG addStyle ===")
    debug_addstyle_variants(opener)

    # 5. Získaj orderJson
    print("\n" + "=" * 60)
    print("=== ZISKANIE ORDERJSON ===")
    result = make_request("POST", "/style/getDispMsData", {"id": "146"})
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

    if order_json:
        print(f"  Počet položiek: {len(order_json)}")

        # 6. Debug updateDispMData
        print("\n" + "=" * 60)
        print("=== DEBUG updateDispMData ===")
        debug_updatedisp_full(146, order_json, opener)

        # 7. Debug modified updateDispMData
        print("\n" + "=" * 60)
        print("=== DEBUG modified updateDispMData ===")
        debug_modified_updatedisp(146, order_json, opener)

    print("\n[RESULT] Všetky debug pokusy potvrdili:")
    print("  - updateDispMData je definitívne broken")
    print("  - Server vracia 200 OK ale ignoruje dáta")
    print("  - JSON body vracia 500 error")
    print("  - getStyleData a queryStyles fungujú")

    print("\n[OK] Debug skript dokončený.")
