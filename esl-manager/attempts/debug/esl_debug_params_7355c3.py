#!/usr/bin/env python3
"""Debug - presny format z tag.js a skus in endpointy."""
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

# 2. Analyzuju tag.js pre presny format
print("\n[2] Analyzuju tag.js pre tag/update...")
with urllib.request.urlopen(f"{ESL_BASE}/app/js/tag.js", timeout=15) as resp:
    tag_js = resp.read().decode("utf-8", errors="replace")

# Hladaj tag/update
idx = tag_js.find("tag/update")
if idx > 0:
    snippet = tag_js[max(0,idx-500):idx+1500]
    print(f"    Kontext:\n{snippet}")

# Hladaj modifyTag
idx2 = tag_js.find("modifyTag")
if idx2 > 0:
    snippet2 = tag_js[max(0,idx2-200):idx2+1000]
    print(f"\n    modifyTag kontext:\n{snippet2}")

# 3. Ziskaj data zo style 146
print("\n[3] Ziskam data zo style 146...")
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

# 4. Skus tag/update s podobnym formatom
print("\n[4] Skusam tag/update...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    form_data = {"id": "146", "orderJson": json_body}
    result = make_request("POST", "/associate/tag/update", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 5. Skus updateDispMData s parametrom "data" namiesto "orderJson"
print("\n[5] Skusam updateDispMData s parametrom data...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    form_data = {"id": "146", "data": json_body}
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")
    
    # Over
    print("\n[6] Overenie...")
    verify = make_request("POST", "/style/getDispMsData", {"id": "146"})
    vraw = verify['text_full']
    if vraw.startswith('"') and vraw.endswith('"'):
        vinner = vraw[1:-1].replace('\\"', '"')
        try:
            vdata = json.loads(vinner)
            print(f"    Prve pole: {vdata[0].get('mpname', '?') if vdata else 'empty'}")
        except:
            print(f"    Nemozem parsovat: {vraw[:200]}")

# 7. Skus updateDispMData s parametrom "json"
print("\n[7] Skusam updateDispMData s parametrom json...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    form_data = {"id": "146", "json": json_body}
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 8. Skus updateDispMData s parametrom "fields"
print("\n[8] Skusam updateDispMData s parametrom fields...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    form_data = {"id": "146", "fields": json_body}
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 9. Skus updateDispMData s parametrom "styleData"
print("\n[9] Skusam updateDispMData s parametrom styleData...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    form_data = {"id": "146", "styleData": json_body}
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 10. Skus updateDispMData s parametrom "dispData"
print("\n[10] Skusam updateDispMData s parametrom dispData...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    form_data = {"id": "146", "dispData": json_body}
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 11. Skus updateDispMData s parametrom "styleJson"
print("\n[11] Skusam updateDispMData s parametrom styleJson...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    form_data = {"id": "146", "styleJson": json_body}
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 12. Skus updateDispMData s parametrom "dispMJson"
print("\n[12] Skusam updateDispMData s parametrom dispMJson...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    form_data = {"id": "146", "dispMJson": json_body}
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")
