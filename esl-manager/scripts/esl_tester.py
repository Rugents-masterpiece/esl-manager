#!/usr/bin/env python3
"""ESL Tester - otestuje všetky endpointy na serveri 192.168.16.251.

Spustenie: python3 esl_tester.py
"""

import json
import urllib.request
import urllib.parse
import base64
import sys

# Konfigurácia
ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"
TIMEOUT = 15

def get(path, params=None):
    """GET request."""
    url = f"{ESL_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    req = urllib.request.Request(url)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("Accept", "*/*")
    
    print(f"  GET {url}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            ct = resp.headers.get("Content-Type", "unknown")
            print(f"  → HTTP {resp.status}, Content-Type: {ct}, Length: {len(data)}")
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  → HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  → CHYBA: {e}")
        return None

def post(path, params=None, form_data=None, json_data=None):
    """POST request."""
    url = f"{ESL_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    body = None
    if json_data is not None:
        body = json.dumps(json_data).encode("utf-8")
        ct = "application/json"
    elif form_data:
        body = urllib.parse.urlencode(form_data, encoding="utf-8").encode("utf-8")
        ct = "application/x-www-form-urlencoded; charset=UTF-8"
    
    req = urllib.request.Request(url, data=body, method="POST")
    if json_data is not None:
        req.add_header("Content-Type", "application/json")
    else:
        req.add_header("Content-Type", ct)
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("Accept", "*/*")
    
    print(f"  POST {url}")
    if body:
        print(f"  → Body: {body[:200]}...")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            ct = resp.headers.get("Content-Type", "unknown")
            print(f"  → HTTP {resp.status}, Content-Type: {ct}, Length: {len(data)}")
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  → HTTP {e.code}: {body[:300]}")
        return None
    except Exception as e:
        print(f"  → CHYBA: {e}")
        return None

def show_json(data, label=""):
    """Vypíše JSON data čitateľne."""
    if not data:
        print(f"  {label} → ŽIADNA ODPOVEĎ")
        return
    try:
        obj = json.loads(data.decode("utf-8"))
        print(f"  {label} → JSON ({len(str(obj))} znakov):")
        # Vypíš len prvé 3 položky ak je to zoznam
        if isinstance(obj, list):
            print(f"    Zoznam s {len(obj)} položkami:")
            for i, item in enumerate(obj[:3]):
                print(f"    [{i}] {json.dumps(item, ensure_ascii=False, indent=4)[:200]}")
            if len(obj) > 3:
                print(f"    ... a {len(obj)-3} ďalších")
        elif isinstance(obj, dict):
            print(f"    {json.dumps(obj, ensure_ascii=False, indent=4)[:500]}")
    except:
        text = data.decode("utf-8", errors="replace")
        print(f"  {label} → TEXT ({len(text)} znakov):")
        print(f"    {text[:300]}")

def main():
    print("=" * 70)
    print("ESL SERVER TESTER")
    print(f"Server: {ESL_BASE}")
    print(f"Session: {SESSION_ID}")
    print("=" * 70)
    
    # 1. GET /associate/getStylesMsg - zoznam šablón
    print("\n[1] GET /associate/getStylesMsg")
    data = get("/associate/getStylesMsg")
    show_json(data, "  Odpoveď")
    
    # 2. GET /associate/getStyleMsgs - so stránkovaním
    print("\n[2] GET /associate/getStyleMsgs?currentPage=0&pageSize=5")
    data = get("/associate/getStyleMsgs", {"currentPage": 0, "pageSize": 5})
    show_json(data, "  Odpoveď")
    
    # 3. POST /associate/getStyleMsgById - detail šablóny
    print("\n[3] POST /associate/getStyleMsgById (body: id=136)")
    data = post("/associate/getStyleMsgById", form_data={"id": "136"})
    show_json(data, "  Odpoveď")
    
    # 4. GET /associate/getTagsMsg - zoznam tagov
    print("\n[4] GET /associate/getTagsMsg")
    data = get("/associate/getTagsMsg")
    show_json(data, "  Odpoveď")
    
    # 5. GET /associate/getRoutersMsg - základné stanice
    print("\n[5] GET /associate/getRoutersMsg")
    data = get("/associate/getRoutersMsg")
    show_json(data, "  Odpoveď")
    
    # 6. GET /associate/getPhotos - zoznam obrázkov
    print("\n[6] GET /associate/getPhotos")
    data = get("/associate/getPhotos")
    show_json(data, "  Odpoveď")
    
    # 7. GET /style/getDispMs?id=X - detail šablóny (style endpoint)
    print("\n[7] GET /style/getDispMs?id=136")
    data = get("/style/getDispMs", {"id": "136"})
    show_json(data, "  Odpoveď")
    
    # 8. GET /style/getDispMs?id=146 - detail šablóny (z tvojho príkladu)
    print("\n[8] GET /style/getDispMs?id=146")
    data = get("/style/getDispMs", {"id": "146"})
    show_json(data, "  Odpoveď")
    
    # 9. GET /associate/getPhotoDataByName - obrázok v base64
    print("\n[9] GET /associate/getPhotoDataByName?photoName=bg1")
    data = get("/associate/getPhotoDataByName", {"photoName": "bg1"})
    show_json(data, "  Odpoveď")
    
    # 10. Skúsime updateDispMData s príkladom z tvojho konzolového výpisu
    print("\n[10] POST /style/updateDispMData?id=146 (testovací request)")
    order_json = [
        {
            "mpname": "Name",
            "prefix": "",
            "name": "text1",
            "style": {
                "z-index": 0, "color": "#000000", "font-weight": 700,
                "text-decoration": "none", "font-size": "13px",
                "background-color": "#ffffff", "board-width": "1px",
                "top": "2px", "left": "1px", "width": "290px",
                "font-family": "HuaweiSans-Light", "height": "50px",
                "text-align": "left", "autoReacting": False
            },
            "id": "2624",
            "text": "Testovacia skladova karta pre overenie maximalnej dlzky nazvu produktu v systeme OBERON",
            "type": "text",
            "suffix": "",
            "feil": "text",
            "table": "tb_tagsandgoods",
            "status": True
        },
        {
            "mpname": "PriceRetail",
            "prefix": "",
            "name": "text2",
            "style": {
                "left": "167px", "top": "55px", "width": "120px",
                "height": "30px", "border-width": "1px",
                "color": "#ffffff", "background-color": "#ff0000",
                "font-family": None, "text-align": "right",
                "font-size": "23px", "line-height": "",
                "font-weight": "700", "text-decoration": "none"
            },
            "id": "2625",
            "text": "999,99",
            "type": "text",
            "suffix": "€",
            "feil": "text",
            "table": "tb_tagsandgoods",
            "status": True
        }
    ]
    data = post("/style/updateDispMData", params={"id": "146"}, form_data={
        "id": "146",
        "orderJson": json.dumps(order_json, ensure_ascii=False)
    })
    show_json(data, "  Odpoveď")
    
    print("\n" + "=" * 70)
    print("TEST UKONČENÝ")
    print("=" * 70)

if __name__ == "__main__":
    main()