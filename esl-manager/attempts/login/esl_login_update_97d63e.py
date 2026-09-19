#!/usr/bin/env python3
"""Login a test update s validnym session."""
import json, urllib.request, urllib.parse, hashlib, re, http.cookiejar

ESL_BASE = "http://192.168.16.251/esls_new"

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
    print(f"    Status: {resp.status}")
    raw = resp.read()
    print(f"    Response: {repr(raw[:200])}")

# 2. Ziskaj orderJson pre style 146
print("\n[2] Ziskujem orderJson...")
req2 = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req2.add_header("X-Requested-With", "XMLHttpRequest")
with opener.open(req2, timeout=15) as resp:
    raw = resp.read()
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith('"') and text.endswith('"'):
        inner = text[1:-1].replace('\\"', '"')
        order_json = json.loads(inner)
    else:
        order_json = json.loads(text)

print(f"    Pocet polov: {len(order_json)}")

# 3. Skopirujem a zmenim ID polov
import copy
new_order = copy.deepcopy(order_json)
new_ids = [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008]
for i, field in enumerate(new_order):
    field["id"] = new_ids[i]
    field["name"] = f"text_{i+1}"

# Zmenim farby na cervene
for field in new_order:
    if field.get("type") == "text" and "color" in field.get("style", {}):
        field["style"]["color"] = "#ff0000"

# 4. Skusam updateDispMData s validnym session
print("\n[3] Skusam updateDispMData...")
json_str = json.dumps(new_order, ensure_ascii=False)
data3 = {"id": "999", "orderJson": json_str}
body3 = urllib.parse.urlencode(data3, encoding="utf-8").encode("utf-8")
req3 = urllib.request.Request(f"{ESL_BASE}/style/updateDispMData", data=body3, method="POST")
req3.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
req3.add_header("X-Requested-With", "XMLHttpRequest")
req3.add_header("Referer", f"{ESL_BASE}/")

with opener.open(req3, timeout=15) as resp:
    raw3 = resp.read()
    print(f"    Status: {resp.status}, Length: {len(raw3)}")
    print(f"    Response: {repr(raw3[:300])}")

# 5. Over
print("\n[4] Overujem sablonu 999...")
req4 = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=999")
req4.add_header("X-Requested-With", "XMLHttpRequest")
try:
    with opener.open(req4, timeout=5) as resp:
        raw4 = resp.read()
        text4 = raw4.decode("utf-8", errors="replace").strip()
        if text4.startswith('"') and text4.endswith('"'):
            inner4 = text4[1:-1].replace('\\"', '"')
            data999 = json.loads(inner4)
        else:
            data999 = json.loads(text4)
        print(f"      Status: {resp.status}, Pocet polov: {len(data999)}")
        if data999:
            print(f"      Prve pole ID: {data999[0].get('id')}")
            red = sum(1 for f in data999 if isinstance(f, dict) and f.get("type") == "text" and f.get("style", {}).get("color") == "#ff0000")
            print(f"      Cervene: {red}/{len(data999)}")
except Exception as e:
    print(f"      Chyba: {e}")

# 6. Over 146
print("\n[5] Overujem sablonu 146...")
req5 = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req5.add_header("X-Requested-With", "XMLHttpRequest")
with opener.open(req5, timeout=15) as resp:
    raw5 = resp.read()
    text5 = raw5.decode("utf-8", errors="replace").strip()
    if text5.startswith('"') and text5.endswith('"'):
        inner5 = text5[1:-1].replace('\\"', '"')
        data146 = json.loads(inner5)
    else:
        data146 = json.loads(text5)
    print(f"      Pocet polov: {len(data146)}")
    red = sum(1 for f in data146 if isinstance(f, dict) and f.get("type") == "text" and f.get("style", {}).get("color") == "#ff0000")
    print(f"      Cervene: {red}/{len(data146)}")
