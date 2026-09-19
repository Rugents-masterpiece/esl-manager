#!/usr/bin/env python3
"""Skusam updateStyle endpoint."""
import json, urllib.request, urllib.parse, copy

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def parse_response(raw):
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith('"') and text.endswith('"'):
        inner = text[1:-1].replace('\\"', '"')
        return json.loads(inner)
    return json.loads(text)

def raw_post(path, data, content_type="application/x-www-form-urlencoded; charset=UTF-8"):
    if isinstance(data, dict):
        body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
    else:
        body = data.encode("utf-8") if isinstance(data, str) else data
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

# 1. Ziskaj orderJson
print("[1] Ziskujem orderJson...")
req = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req.add_header("X-Requested-With", "XMLHttpRequest")
with urllib.request.urlopen(req, timeout=15) as resp:
    order_json = parse_response(resp.read())

print(f"    Pocet polov: {len(order_json)}")

# 2. Skopirujem a zmenim ID polov
new_order = copy.deepcopy(order_json)
new_ids = [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008]
for i, field in enumerate(new_order):
    field["id"] = new_ids[i]
    field["name"] = f"text_{i+1}"

# Zmenim farby na cervene
for field in new_order:
    if field.get("type") == "text" and "color" in field.get("style", {}):
        field["style"]["color"] = "#ff0000"

# 3. Skusam updateStyle endpoint
print("\n[2] Skusam updateStyle...")
json_str = json.dumps(new_order, ensure_ascii=False)

# Skusam viac sposobov
methods = [
    ("updateStyle: id + orderJson", {"id": "999", "orderJson": json_str}),
    ("updateStyle: id=999, orderJson=...", {"id": 999, "orderJson": json_str}),
    ("updateStyleMsg: id + orderJson", {"id": "999", "orderJson": json_str}),
    ("updateStyleMsg: id=999, orderJson=...", {"id": 999, "orderJson": json_str}),
]

for name, data in methods:
    print(f"\n    --- {name} ---")
    status, raw = raw_post("/style/updateStyle", data)
    print(f"      Status: {status}, Length: {len(raw)}")
    print(f"      Response: {repr(raw[:300])}")

# 4. Skusam aj updateDispMData s JSON body
print("\n[3] Skusam updateDispMData s JSON body...")
json_body = json.dumps({"id": 999, "orderJson": new_order}, ensure_ascii=False)
status, raw = raw_post("/style/updateDispMData", json_body, "application/json")
print(f"      Status: {status}, Length: {len(raw)}")
print(f"      Response: {repr(raw[:300])}")

# 5. Over
print("\n[4] Overujem sablonu 999...")
req2 = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=999")
req2.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req2.add_header("X-Requested-With", "XMLHttpRequest")
try:
    with urllib.request.urlopen(req2, timeout=5) as resp:
        data = parse_response(resp.read())
        print(f"      Status: {resp.status}, Pocet polov: {len(data)}")
        if data:
            print(f"      Prve pole ID: {data[0].get('id')}")
            red = sum(1 for f in data if isinstance(f, dict) and f.get("type") == "text" and f.get("style", {}).get("color") == "#ff0000")
            print(f"      Cervene: {red}/{len(data)}")
except Exception as e:
    print(f"      Chyba: {e}")
