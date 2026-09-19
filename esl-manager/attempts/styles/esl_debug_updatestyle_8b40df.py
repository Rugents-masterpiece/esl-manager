#!/usr/bin/env python3
"""Debug - presny format updateDispMData z JavaScriptu."""
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

# 2. Analyzuju style.js pre updateStyle a updateDispMData
print("\n[2] Analyzuju style.js pre updateStyle...")
with urllib.request.urlopen(f"{ESL_BASE}/app/js/style.js", timeout=15) as resp:
    style_js = resp.read().decode("utf-8", errors="replace")

# Hladaj updateStyle funkciu
idx = style_js.find("updateStyle")
if idx > 0:
    print(f"    NASHIEL updateStyle na pozicii {idx}")
    snippet = style_js[max(0,idx-500):idx+1500]
    print(f"    Kontext:\n{snippet}")

# Hladaj updateDispMData
print("\n[3] Hladam updateDispMData v style.js...")
idx2 = style_js.find("updateDispMData")
if idx2 > 0:
    print(f"    NASHIEL updateDispMData na pozicii {idx2}")
    snippet2 = style_js[max(0,idx2-500):idx2+1500]
    print(f"    Kontext:\n{snippet2}")
else:
    print("    updateDispMData NENASHIEL v style.js")

# Hladaj vsetky endpointy v style.js
print("\n[4] Vsetky endpointy v style.js...")
urls = set(re.findall(r'["\'](/?style/[^"\']+)["\']', style_js))
for u in sorted(urls):
    print(f"  {u}")

# Hladaj ajax call s url
print("\n[5] Vsetky ajax url v style.js...")
ajax_urls = set(re.findall(r'url\s*:\s*["\']([^"\']+)["\']', style_js))
for u in sorted(ajax_urls):
    print(f"  {u}")

# 6. Skus updateStyle na style 146
print("\n[6] updateStyle na style 146...")
# Ziskaj data zo style 146
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
    # Zmen prve pole
    modified = copy.deepcopy(order_json)
    modified[0]["mpname"] = "CHANGED_TEST_146"
    json_str = json.dumps(modified, ensure_ascii=False)
    
    # Skus s form-urlencoded
    form_data = {
        "id": "146",
        "orderJson": json_str
    }
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")
    
    # Over
    print("\n[7] Overenie zmeny v 146...")
    verify = make_request("POST", "/style/getDispMsData", {"id": "146"})
    vraw = verify['text_full']
    if vraw.startswith('"') and vraw.endswith('"'):
        vinner = vraw[1:-1].replace('\\"', '"')
        try:
            vdata = json.loads(vinner)
            print(f"    Prve pole: {vdata[0].get('mpname', '?') if vdata else 'empty'}")
        except:
            print(f"    Nemozem parsovat: {vraw[:200]}")
    else:
        print(f"    Response: {vraw[:300]}")

# 8. Skus updateStyle endpoint (nie updateDispMData)
print("\n[8] Skusam updateStyle endpoint...")
if order_json and isinstance(order_json, list):
    # Skus s JSON body
    update_json = json.dumps({
        "id": 146,
        "orderJson": order_json
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")
    
    # Skus s form-urlencoded
    form_data2 = {
        "id": "146",
        "orderJson": json_str
    }
    result2 = make_request("POST", "/style/updateStyle", form_data2)
    print(f"    Status: {result2['status']}")
    print(f"    Response: {result2['text'][:300]}")

# 9. Skus updateStyleMsg
print("\n[9] Skusam updateStyleMsg...")
if order_json and isinstance(order_json, list):
    form_data3 = {
        "id": "146",
        "orderJson": json_str
    }
    result3 = make_request("POST", "/style/updateStyleMsg", form_data3)
    print(f"    Status: {result3['status']}")
    print(f"    Response: {result3['text'][:300]}")

# 10. Skus associate/updateDispMData
print("\n[10] Skusam associate/updateDispMData...")
if order_json and isinstance(order_json, list):
    form_data4 = {
        "id": "146",
        "orderJson": json_str
    }
    result4 = make_request("POST", "/associate/updateDispMData", form_data4)
    print(f"    Status: {result4['status']}")
    print(f"    Response: {result4['text'][:300]}")

# 11. Skus associate/updateStyle
print("\n[11] Skusam associate/updateStyle...")
if order_json and isinstance(order_json, list):
    form_data5 = {
        "id": "146",
        "orderJson": json_str
    }
    result5 = make_request("POST", "/associate/updateStyle", form_data5)
    print(f"    Status: {result5['status']}")
    print(f"    Response: {result5['text'][:300]}")

# 12. Skus associate/updateStyleMsg
print("\n[12] Skusam associate/updateStyleMsg...")
if order_json and isinstance(order_json, list):
    form_data6 = {
        "id": "146",
        "orderJson": json_str
    }
    result6 = make_request("POST", "/associate/updateStyleMsg", form_data6)
    print(f"    Status: {result6['status']}")
    print(f"    Response: {result6['text'][:300]}")
