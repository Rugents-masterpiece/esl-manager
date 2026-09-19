#!/usr/bin/env python3
"""Test updateDispMData - skusam poslat orderJson bez zmien."""
import json, urllib.request, urllib.parse

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def raw_post(path, params=None, form_data=None):
    url = f"{ESL_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    body = None
    if form_data:
        body = urllib.parse.urlencode(form_data, encoding="utf-8").encode("utf-8")
    
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return {"status": resp.status, "raw": raw, "text": raw.decode("utf-8", errors="replace"), "length": len(raw)}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return {"status": e.code, "raw": raw, "text": raw.decode("utf-8", errors="replace"), "length": len(raw)}

# 1. Ziskaj orderJson a over struktúru
print("[1] Ziskujem orderJson zo style 146...")
resp = raw_post("/style/getDispMsData", params={"id": "146"})
text = resp['text'].strip()

if text.startswith('"') and text.endswith('"'):
    inner = text[1:-1].replace('\\"', '"')
    order_json = json.loads(inner)
else:
    order_json = json.loads(text)

print(f"    Pocet polov: {len(order_json)}")
print(f"    Prve pole: {json.dumps(order_json[0], indent=2, ensure_ascii=False)[:500]}")

# 2. Skusam poslat orderJson bez akychkolvek zmien
print("\n[2] Skusam poslat orderJson bez zmien...")
json_str = json.dumps(order_json, ensure_ascii=False)
print(f"    orderJson length: {len(json_str)}")
print(f"    First 200 chars: {repr(json_str[:200])}")

resp2 = raw_post("/style/updateDispMData", params={"id": "146"}, form_data={"id": "146", "orderJson": json_str})
print(f"    Response status: {resp2['status']}, length: {resp2['length']}")
print(f"    Response text: {repr(resp2['text'][:200])}")

# 3. Over ci sa nieco zmenilo
print("\n[3] Overujem...")
resp3 = raw_post("/style/getDispMsData", params={"id": "146"})
text3 = resp3['text'].strip()
if text3.startswith('"') and text3.endswith('"'):
    inner3 = text3[1:-1].replace('\\"', '"')
    verify = json.loads(inner3)
else:
    verify = json.loads(text3)

print(f"    Pocet polov po update: {len(verify)}")
print(f"    Prve pole: {json.dumps(verify[0], indent=2, ensure_ascii=False)[:500]}")

# 4. Skusam s inym style - napr. style 1
print("\n[4] Skusam style 1...")
resp4 = raw_post("/style/getDispMsData", params={"id": "1"})
text4 = resp4['text'].strip()
if text4.startswith('"') and text4.endswith('"'):
    inner4 = text4[1:-1].replace('\\"', '"')
    order_json_1 = json.loads(inner4)
else:
    order_json_1 = json.loads(text4)

print(f"    Pocet polov style 1: {len(order_json_1)}")

# Zmen farbu na style 1
for f in order_json_1:
    if isinstance(f, dict) and f.get("type") == "text":
        f["style"]["color"] = "#ff0000"

json_str_1 = json.dumps(order_json_1, ensure_ascii=False)
resp5 = raw_post("/style/updateDispMData", params={"id": "1"}, form_data={"id": "1", "orderJson": json_str_1})
print(f"    Response status: {resp5['status']}, length: {resp5['length']}")

# Over style 1
resp6 = raw_post("/style/getDispMsData", params={"id": "1"})
text6 = resp6['text'].strip()
if text6.startswith('"') and text6.endswith('"'):
    inner6 = text6[1:-1].replace('\\"', '"')
    verify1 = json.loads(inner6)
else:
    verify1 = json.loads(text6)

red1 = sum(1 for f in verify1 if isinstance(f, dict) and f.get("type") == "text" and f.get("style", {}).get("color") == "#ff0000")
print(f"    Cervene na style 1: {red1}/{len(verify1)}")

# 5. Skusam poslat len orderJson bez id v params
print("\n[5] Skusam updateDispMData len s orderJson v body...")
json_str_146 = json.dumps(order_json, ensure_ascii=False)
resp7 = raw_post("/style/updateDispMData", form_data={"orderJson": json_str_146})
print(f"    Response status: {resp7['status']}, length: {resp7['length']}")

# 6. Skusam poslat orderJson ako JSON string v orderJson param
print("\n[6] Skusam poslat orderJson ako JSON string...")
resp8 = raw_post("/style/updateDispMData", form_data={"id": "146", "orderJson": json_str_146})
print(f"    Response status: {resp8['status']}, length: {resp8['length']}")

# 7. Skusam poslat orderJson bez escaped uvozoviek
print("\n[7] Skusam poslat orderJson bez escaped uvozoviek...")
# Skusam poslat orderJson priamo ako JSON string
resp9 = raw_post("/style/updateDispMData", form_data={"id": "146", "orderJson": json_str_146})
print(f"    Response status: {resp9['status']}, length: {resp9['length']}")

# 8. Skusam poslat orderJson ako JSON array v tele
print("\n[8] Skusam poslat orderJson ako JSON v tele...")
req = urllib.request.Request(
    f"{ESL_BASE}/style/updateDispMData",
    data=json_str_146.encode("utf-8"),
    method="POST"
)
req.add_header("Content-Type", "application/json")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req.add_header("X-Requested-With", "XMLHttpRequest")

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
        print(f"    Response status: {resp.status}, length: {len(raw)}")
        print(f"    Response text: {repr(raw.decode('utf-8', errors='replace')[:200])}")
except urllib.error.HTTPError as e:
    raw = e.read()
    print(f"    HTTP {e.code}, length: {len(raw)}")
    print(f"    Response text: {repr(raw.decode('utf-8', errors='replace')[:200])}")
