#!/usr/bin/env python3
"""Test updateDispMData s presnymi hlavičkami."""
import json, urllib.request, urllib.parse

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

# 1. Ziskaj orderJson
print("[1] Ziskujem orderJson...")
req = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req.add_header("X-Requested-With", "XMLHttpRequest")
with urllib.request.urlopen(req, timeout=15) as resp:
    raw = resp.read()
    text = raw.decode("utf-8", errors="replace").strip()

if text.startswith('"') and text.endswith('"'):
    inner = text[1:-1].replace('\\"', '"')
    order_json = json.loads(inner)
else:
    order_json = json.loads(text)

print(f"    Pocet polov: {len(order_json)}")

# 2. Zmen farbu na prvom poli
for f in order_json:
    if isinstance(f, dict) and f.get("type") == "text":
        f["style"]["color"] = "#ff0000"
        break

# 3. Skusam poslat s presnymi hlavičkami z dashboardu
print("\n[2] Skusam update s presnymi hlavičkami...")
json_str = json.dumps(order_json, ensure_ascii=False)

# Skusam viac sposobov
methods = [
    ("form-urlencoded", {"id": "146", "orderJson": json_str}),
    ("json body", json.dumps({"id": 146, "orderJson": order_json}, ensure_ascii=False)),
    ("json body only orderJson", json.dumps(order_json, ensure_ascii=False)),
]

for name, data in methods:
    print(f"\n    --- {name} ---")
    if isinstance(data, str):
        body = data.encode("utf-8")
        ct = "application/json"
    else:
        body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
        ct = "application/x-www-form-urlencoded; charset=UTF-8"
    
    req = urllib.request.Request(
        f"{ESL_BASE}/style/updateDispMData",
        data=body,
        method="POST"
    )
    req.add_header("Content-Type", ct)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Referer", f"{ESL_BASE}/")
    req.add_header("Origin", ESL_BASE)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            print(f"      Status: {resp.status}, Length: {len(raw)}")
            print(f"      Response: {repr(raw[:200])}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        print(f"      HTTP {e.code}, Length: {len(raw)}")
        print(f"      Response: {repr(raw[:200])}")

# 4. Over
print("\n[3] Overujem...")
req2 = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req2.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req2.add_header("X-Requested-With", "XMLHttpRequest")
with urllib.request.urlopen(req2, timeout=15) as resp:
    raw2 = resp.read()
    text2 = raw2.decode("utf-8", errors="replace").strip()

if text2.startswith('"') and text2.endswith('"'):
    inner2 = text2[1:-1].replace('\\"', '"')
    verify = json.loads(inner2)
else:
    verify = json.loads(text2)

red = sum(1 for f in verify if isinstance(f, dict) and f.get("type") == "text" and f.get("style", {}).get("color") == "#ff0000")
print(f"    Cervene: {red}/{len(verify)}")
