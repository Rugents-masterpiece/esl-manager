#!/usr/bin/env python3
"""Vytvori novu sablonu cez addStyle a napln ju datami z 146."""
import json, urllib.request, urllib.parse, hashlib, re, http.cookiejar, copy

ESL_BASE = "http://192.168.16.251/esls_new"

def parse_response(raw):
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith('"') and text.endswith('"'):
        inner = text[1:-1].replace('\\"', '"')
        return json.loads(inner)
    return json.loads(text)

def raw_post(path, data, content_type="application/x-www-form-urlencoded; charset=UTF-8"):
    if isinstance(data, dict):
        body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
    elif isinstance(data, str):
        body = data.encode("utf-8")
    else:
        body = data
    req = urllib.request.Request(f"{ESL_BASE}{path}", data=body, method="POST")
    req.add_header("Content-Type", content_type)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, raw

# 1. Login
print("[1] Login...")
passwd_md5 = hashlib.md5(b"admin").hexdigest()
data = {"username": "admin", "passwd": passwd_md5}
body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
req = urllib.request.Request(f"{ESL_BASE}/login/userLogin", data=body, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
req.add_header("X-Requested-With", "XMLHttpRequest")

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

with opener.open(req, timeout=15) as resp:
    raw = resp.read()
    SESSION_ID = None
    for cookie in cj:
        if cookie.name == "JSESSIONID":
            SESSION_ID = cookie.value
            break
    print(f"    Session: {SESSION_ID[:20] if SESSION_ID else 'NONE'}...")

# 2. Ziskaj orderJson pre style 146
print("\n[2] Ziskujem orderJson pre style 146...")
req = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req.add_header("X-Requested-With", "XMLHttpRequest")
with opener.open(req, timeout=15) as resp:
    order_json = parse_response(resp.read())

print(f"    Pocet polov: {len(order_json)}")
print(f"    Struktura prveho pola: {json.dumps(order_json[0], indent=4, ensure_ascii=False)[:500]}")

# 3. Vytvor novu sablonu cez addStyle
print("\n[3] Vytvaram novu sablonu cez addStyle...")
new_style_data = json.dumps({
    "name": "Klon_146_cervena",
    "type": "1",
    "mappingtype": "1"
}, ensure_ascii=False)

status, raw = raw_post("/style/addStyle", new_style_data, "application/json")
print(f"    Status: {status}, Response: {repr(raw[:200])}")

# 4. Ziskaj zoznam style a najdi novu
print("\n[4] Hladam novu sablonu v zozname...")
req = urllib.request.Request(f"{ESL_BASE}/style/getStylesData?currentPage=1&pageSize=100")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req.add_header("X-Requested-With", "XMLHttpRequest")
with opener.open(req, timeout=15) as resp:
    raw = resp.read()
    text = raw.decode("utf-8", errors="replace").strip()
    
    if text.startswith('"') and text.endswith('"'):
        inner = text[1:-1].replace('\\"', '"')
        styles_data = json.loads(inner)
    else:
        styles_data = json.loads(text)

print(f"    Typ odpovede: {type(styles_data)}")
if isinstance(styles_data, dict):
    print(f"    Klucove: {list(styles_data.keys())}")
    for key in styles_data.keys():
        val = styles_data[key]
        if isinstance(val, list):
            print(f"    {key}: {len(val)} poloziek")
            for s in val[-5:]:  # Posledne 5
                print(f"      ID={s.get('id')}, Name={s.get('name')}, Type={s.get('type')}")
        elif isinstance(val, str):
            print(f"    {key}: {val[:100]}")
elif isinstance(styles_data, list):
    print(f"    Pocet style: {len(styles_data)}")
    for s in styles_data[-5:]:  # Posledne 5
        print(f"      ID={s.get('id')}, Name={s.get('name')}, Type={s.get('type')}")

# 5. Skusam najst novu sablonu s menom "Klon_146_cervena"
print("\n[5] Hladam 'Klon_146_cervena'...")
found_id = None
if isinstance(styles_data, dict):
    for key in styles_data.keys():
        val = styles_data[key]
        if isinstance(val, list):
            for s in val:
                if isinstance(s, dict) and s.get('name') == 'Klon_146_cervena':
                    found_id = s.get('id')
                    print(f"      NASHIEL: ID={found_id}")
                    break
elif isinstance(styles_data, list):
    for s in styles_data:
        if isinstance(s, dict) and s.get('name') == 'Klon_146_cervena':
            found_id = s.get('id')
            print(f"      NASHIEL: ID={found_id}")
            break

if not found_id:
    print("      Nenashiel - vypisujem vsetky s 'Klon' v mene:")
    if isinstance(styles_data, dict):
        for key in styles_data.keys():
            val = styles_data[key]
            if isinstance(val, list):
                for s in val:
                    if isinstance(s, dict) and 'Klon' in str(s.get('name', '')):
                        print(f"      ID={s.get('id')}, Name={s.get('name')}")
    elif isinstance(styles_data, list):
        for s in styles_data:
            if isinstance(s, dict) and 'Klon' in str(s.get('name', '')):
                print(f"      ID={s.get('id')}, Name={s.get('name')}")

# 6. Ak nasli ID, skus updateDispMData
if found_id:
    print(f"\n[6] Skusam updateDispMData s ID={found_id}...")
    
    # Skopirujem a zmenim ID polov
    new_order = copy.deepcopy(order_json)
    new_ids = [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008]
    for i, field in enumerate(new_order):
        field["id"] = new_ids[i]
        field["name"] = f"text_{i+1}"
    
    # Zmenim farby na cervene
    for field in new_order:
        if field.get("type") == "text" and "color" in field.get("style", {}):
            field["style"]["color"] = "#ff0000"
    
    json_str = json.dumps(new_order, ensure_ascii=False)
    data = {"id": str(found_id), "orderJson": json_str}
    status, raw = raw_post("/style/updateDispMData", data)
    print(f"    Status: {status}, Length: {len(raw)}")
    print(f"    Response: {repr(raw[:300])}")
    
    # 7. Over
    print(f"\n[7] Overujem novu sablonu {found_id}...")
    req = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id={found_id}")
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    try:
        with opener.open(req, timeout=5) as resp:
            data = parse_response(resp.read())
            print(f"      Pocet polov: {len(data)}")
            if data:
                red = sum(1 for f in data if isinstance(f, dict) and f.get("type") == "text" and f.get("style", {}).get("color") == "#ff0000")
                print(f"      Cervene: {red}/{len(data)}")
                print(f"      Prve pole ID: {data[0].get('id')}")
    except Exception as e:
        print(f"      Chyba: {e}")

# 8. Over 146
print("\n[8] Overujem puvodnu sablonu 146...")
req = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req.add_header("X-Requested-With", "XMLHttpRequest")
with opener.open(req, timeout=15) as resp:
    data = parse_response(resp.read())
    print(f"    Pocet polov: {len(data)}")
    red = sum(1 for f in data if isinstance(f, dict) and f.get("type") == "text" and f.get("style", {}).get("color") == "#ff0000")
    print(f"    Cervene: {red}/{len(data)}")
