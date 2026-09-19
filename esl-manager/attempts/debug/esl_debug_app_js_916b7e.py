#!/usr/bin/env python3
"""Analyzuje app.js a skusam updateDispMData s presnym formatom."""
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

# 2. Analyzuju app.js
print("\n[2] Analyzuju app.js...")
with urllib.request.urlopen(f"{ESL_BASE}/assets/scripts/app.js", timeout=15) as resp:
    app_js = resp.read().decode("utf-8", errors="replace")

print(f"    Length: {len(app_js)}")

# Hladaj vsetky endpointy
urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', app_js))
print(f"    Endpointy ({len(urls)}):")
for u in sorted(urls):
    print(f"      {u}")

# Hladaj ajax call
ajax_urls = set(re.findall(r'url\s*:\s*["\']([^"\']+)["\']', app_js))
print(f"\n    Ajax urls ({len(ajax_urls)}):")
for u in sorted(ajax_urls):
    print(f"      {u}")

# Hladaj updateDispMData
if "updateDispMData" in app_js:
    print("\n    NASHIEL updateDispMData v app.js!")
    idx = app_js.find("updateDispMData")
    snippet = app_js[max(0,idx-500):idx+1500]
    print(f"    Kontext:\n{snippet}")

# 3. Skus updateDispMData s presnym formatom
print("\n[3] Skusam updateDispMData s presnym formatom...")

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
    
    # Skus s JSON body
    json_body = json.dumps(modified, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData?id=146", json_body, "application/json")
    print(f"    [3a] JSON body: Status={result['status']}, Response={result['text'][:200]}")
    
    # Skus s form-urlencoded
    form_data = {"orderJson": json_body}
    result2 = make_request("POST", "/style/updateDispMData?id=146", form_data)
    print(f"    [3b] form-urlencoded: Status={result2['status']}, Response={result2['text'][:200]}")
    
    # Skus s form-urlencoded a id aj orderJson
    form_data2 = {"id": "146", "orderJson": json_body}
    result3 = make_request("POST", "/style/updateDispMData", form_data2)
    print(f"    [3c] form-urlencoded (id+orderJson): Status={result3['status']}, Response={result3['text'][:200]}")
    
    # Skus s form-urlencoded a id len v URL
    form_data3 = {"orderJson": json_body}
    result4 = make_request("POST", "/style/updateDispMData?id=146", form_data3)
    print(f"    [3d] form-urlencoded (len orderJson, id v URL): Status={result4['status']}, Response={result4['text'][:200]}")
    
    # Over
    print("\n[4] Overenie zmeny v 146...")
    verify = make_request("POST", "/style/getDispMsData", {"id": "146"})
    vraw = verify['text_full']
    if vraw.startswith('"') and vraw.endswith('"'):
        vinner = vraw[1:-1].replace('\\"', '"')
        try:
            vdata = json.loads(vinner)
            print(f"    Prve pole mpname: {vdata[0].get('mpname', '?') if vdata else 'empty'}")
        except:
            print(f"    Nemozem parsovat: {vraw[:200]}")
    else:
        print(f"    Response: {vraw[:300]}")

# 5. Skus updateDispMData na style 152 (ktora sme vytvorili)
print("\n[5] updateDispMData na style 152...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    
    # Skus s JSON body
    result = make_request("POST", "/style/updateDispMData?id=152", json_body, "application/json")
    print(f"    [5a] JSON body: Status={result['status']}, Response={result['text'][:200]}")
    
    # Skus s form-urlencoded
    form_data = {"orderJson": json_body}
    result2 = make_request("POST", "/style/updateDispMData?id=152", form_data)
    print(f"    [5b] form-urlencoded: Status={result2['status']}, Response={result2['text'][:200]}")
    
    # Over
    print("\n[6] Overenie - getDispMsData pre 152...")
    verify = make_request("POST", "/style/getDispMsData", {"id": "152"})
    vraw = verify['text_full']
    print(f"    Response: {vraw[:300]}")
