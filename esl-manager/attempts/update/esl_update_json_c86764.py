#!/usr/bin/env python3
"""Test updateDispMData s JSON body."""
import json, urllib.request, urllib.parse, hashlib, re, http.cookiejar, copy

ESL_BASE = "http://192.168.16.251/esls_new"

def parse_response(raw):
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith('"') and text.endswith('"'):
        inner = text[1:-1].replace('\\"', '"')
        return json.loads(inner)
    return json.loads(text)

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

# 2. Ziskaj orderJson pre style 146
print("\n[2] Ziskujem orderJson pre style 146...")
req = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req.add_header("X-Requested-With", "XMLHttpRequest")
with opener.open(req, timeout=15) as resp:
    order_json = parse_response(resp.read())

print(f"    Pocet polov: {len(order_json)}")

# 3. Skopirujem a zmenim ID polov
new_order = copy.deepcopy(order_json)
new_ids = [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008]
for i, field in enumerate(new_order):
    field["id"] = new_ids[i]
    field["name"] = f"text_{i+1}"

# Zmenim farby na cervene
for field in new_order:
    if field.get("type") == "text" and "color" in field.get("style", {}):
        field["style"]["color"] = "#ff0000"

# 4. Skusam updateDispMData s JSON body
print("\n[3] Skusam updateDispMData s JSON body...")
json_body = json.dumps({"id": 152, "orderJson": new_order}, ensure_ascii=False)
req = urllib.request.Request(
    f"{ESL_BASE}/style/updateDispMData",
    data=json_body.encode("utf-8"),
    method="POST"
)
req.add_header("Content-Type", "application/json")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req.add_header("X-Requested-With", "XMLHttpRequest")
req.add_header("Referer", f"{ESL_BASE}/main/index")

try:
    with opener.open(req, timeout=15) as resp:
        raw = resp.read()
        print(f"    Status: {resp.status}, Length: {len(raw)}")
        print(f"    Response: {repr(raw[:500])}")
except urllib.error.HTTPError as e:
    raw = e.read()
    print(f"    HTTP {e.code}, Length: {len(raw)}")
    print(f"    Response: {repr(raw[:500])}")

# 5. Over
print("\n[4] Overujem sablonu 152...")
req = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=152")
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
            print(f"      Prve pole: {json.dumps(data[0], indent=4, ensure_ascii=False)[:500]}")
except Exception as e:
    print(f"      Chyba: {e}")
