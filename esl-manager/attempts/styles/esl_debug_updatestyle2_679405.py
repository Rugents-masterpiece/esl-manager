#!/usr/bin/env python3
"""Debug - presny format updateStyle z JavaScriptu + skus in endpointy."""
import json, urllib.request, urllib.parse, hashlib, http.cookiejar, copy, re

ESL_BASE = "http://192.168.16.251/esls_new"

def make_request(method, path, data=None, content_type="application/x-www-form-urlencoded; charset=UTF-8"):
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
            }
    except urllib.error.HTTPError as e:
        raw = e.read()
        text = raw.decode("utf-8", errors="replace").strip()
        return {
            "status": e.code,
            "text": text[:500],
            "text_full": text,
            "error": True,
        }

# 1. Login
print("[1] Login...")
passwd_md5 = hashlib.md5(b"admin").hexdigest()
result = make_request("POST", "/login/userLogin", {"username": "admin", "passwd": passwd_md5})
print(f"    Status: {result['status']}")

# 2. Ziskaj data zo style 146
print("\n[2] Ziskam data zo style 146...")
disp_result = make_request("POST", "/style/getDispMsData", {"id": "146"})
raw_text = disp_result['text_full']
order_json = None
if raw_text.startswith('"') and raw_text.endswith('"'):
    inner = raw_text[1:-1].replace('\\"', '"')
    try: order_json = json.loads(inner)
    except: pass
elif raw_text.startswith('['):
    try: order_json = json.loads(raw_text)
    except: pass

if order_json and isinstance(order_json, list):
    print(f"    Pocet polov: {len(order_json)}")
    print(f"    Prve pole: {json.dumps(order_json[0], ensure_ascii=False)[:200]}")

# 3. Ziskaj getStyleData pre 146
print("\n[3] getStyleData pre 146...")
result = make_request("GET", "/style/getStyleData", {"id": "146"})
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")

# 4. Skus updateStyle s JSON body presne tak ako to robi JS
print("\n[4] updateStyle s JSON body (presne ako JS)...")
# Z JS: ss.name, ss.type, ss.descriptor, ss.rotate, ss.sid
update_json = json.dumps({
    "name": "Rudo_TEST",
    "type": "1",
    "descriptor": "Rudo",
    "rotate": "0",
    "sid": "146"
}, ensure_ascii=False)
result = make_request("POST", "/style/updateStyle", update_json, "application/json")
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 5. Skus updateStyle s JSON body a orderJson
print("\n[5] updateStyle s JSON body a orderJson...")
if order_json and isinstance(order_json, list):
    update_json2 = json.dumps({
        "id": 146,
        "name": "Rudo_TEST2",
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": "146",
        "orderJson": order_json
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json2, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 6. Skus updateStyle s JSON body a fields
print("\n[6] updateStyle s JSON body a fields...")
if order_json and isinstance(order_json, list):
    update_json3 = json.dumps({
        "id": 146,
        "name": "Rudo_TEST3",
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": "146",
        "fields": order_json
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json3, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 7. Skus updateStyle s JSON body a order_json
print("\n[7] updateStyle s JSON body a order_json...")
if order_json and isinstance(order_json, list):
    update_json4 = json.dumps({
        "id": 146,
        "name": "Rudo_TEST4",
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": "146",
        "order_json": order_json
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json4, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 8. Skus updateStyle s JSON body a data
print("\n[8] updateStyle s JSON body a data...")
if order_json and isinstance(order_json, list):
    update_json5 = json.dumps({
        "id": 146,
        "name": "Rudo_TEST5",
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": "146",
        "data": order_json
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json5, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 9. Skus updateStyle s JSON body a dispMData
print("\n[9] updateStyle s JSON body a dispMData...")
if order_json and isinstance(order_json, list):
    update_json6 = json.dumps({
        "id": 146,
        "name": "Rudo_TEST6",
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": "146",
        "dispMData": order_json
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json6, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 10. Skus updateStyle s JSON body a styleData
print("\n[10] updateStyle s JSON body a styleData...")
if order_json and isinstance(order_json, list):
    update_json7 = json.dumps({
        "id": 146,
        "name": "Rudo_TEST7",
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": "146",
        "styleData": order_json
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json7, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 11. Skus updateStyle s JSON body a styleJson
print("\n[11] updateStyle s JSON body a styleJson...")
if order_json and isinstance(order_json, list):
    update_json8 = json.dumps({
        "id": 146,
        "name": "Rudo_TEST8",
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": "146",
        "styleJson": order_json
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json8, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 12. Skus updateStyle s JSON body a json
print("\n[12] updateStyle s JSON body a json...")
if order_json and isinstance(order_json, list):
    update_json9 = json.dumps({
        "id": 146,
        "name": "Rudo_TEST9",
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": "146",
        "json": order_json
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json9, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 13. Over getStyleData po update
print("\n[13] Over getStyleData po update...")
result = make_request("GET", "/style/getStyleData", {"id": "146"})
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")
