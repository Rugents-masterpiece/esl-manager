#!/usr/bin/env python3
"""Debug - najdi spravny endpoint na klonovanie sablony."""
import json, urllib.request, urllib.parse, hashlib, http.cookiejar, copy

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

# 3. addStyle s JSON body
print("\n[3] addStyle s JSON body...")
create_json = json.dumps({
    "name": "Klon_146_Test",
    "type": "1",
    "descriptor": "Template_Klon",
    "rotate": "0",
    "sid": "1"
}, ensure_ascii=False)
result = make_request("POST", "/style/addStyle", create_json, "application/json")
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 4. style/addStyle s JSON body
print("\n[4] style/addStyle s JSON body...")
result = make_request("POST", "/style/addStyle", create_json, "application/json")
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 5. associate/addStyle s JSON body
print("\n[5] associate/addStyle s JSON body...")
result = make_request("POST", "/associate/addStyle", create_json, "application/json")
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 6. Ziskaj vsetky style a najdi najvyssie ID
print("\n[6] Ziskam vsetky style...")
styles_result = make_request("POST", "/style/getStyleMsgs", {})
raw = styles_result['text_full']
print(f"    Status: {styles_result['status']}")
print(f"    Response: {raw[:500]}")

# 7. getStyleMsgs (GET)
print("\n[7] getStyleMsgs GET...")
result = make_request("GET", "/associate/getStyleMsgs", {"currentPage": "0", "pageSize": "100"})
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")

# 8. Skus getStylesData
print("\n[8] getStylesData...")
result = make_request("POST", "/style/getStylesData", {})
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")

# 9. Skus addStyle s form-urlencoded (ako to robi dashboard)
print("\n[9] addStyle s form-urlencoded...")
form_data = {"name": "Klon_146_Test2", "type": "1", "descriptor": "Template_Klon2", "rotate": "0", "sid": "1"}
result = make_request("POST", "/style/addStyle", form_data)
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 10. Skus addStyle s form-urlencoded na associate/addStyle
print("\n[10] associate/addStyle s form-urlencoded...")
result = make_request("POST", "/associate/addStyle", form_data)
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 11. Skus addStyle s form-urlencoded na style/addStyle
print("\n[11] style/addStyle s form-urlencoded...")
result = make_request("POST", "/style/addStyle", form_data)
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 12. Skus style/addStyleMsg
print("\n[12] style/addStyleMsg...")
result = make_request("POST", "/style/addStyleMsg", form_data)
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 13. Skus associate/addStyleMsg
print("\n[13] associate/addStyleMsg...")
result = make_request("POST", "/associate/addStyleMsg", form_data)
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 14. Ziskaj vsetky endpointy z style.js
print("\n[14] Analyzuju style.js...")
try:
    with urllib.request.urlopen(f"{ESL_BASE}/app/js/style.js", timeout=15) as resp:
        style_js = resp.read().decode("utf-8", errors="replace")
        # Hladaj vsetky URL endpointy
        urls = set()
        for m in __import__('re').finditer(r'["\'](/esls_new/[^"\']+)["\']', style_js):
            urls.add(m.group(1))
        for m in __import__('re').finditer(r'["\']([^"\']*style[^"\']*)["\']', style_js):
            urls.add(m.group(1))
        for m in __import__('re').finditer(r'["\'](/[^"\']*style[^"\']*)["\']', style_js):
            urls.add(m.group(1))
        print(f"    NASHIEL endpointy:")
        for u in sorted(urls):
            print(f"      {u}")
except Exception as e:
    print(f"    Chyba: {e}")

# 15. Skus style/addStyleMsg s JSON
print("\n[15] style/addStyleMsg s JSON...")
result = make_request("POST", "/style/addStyleMsg", create_json, "application/json")
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")

# 16. Skus style/addStyleMsg s form-urlencoded
print("\n[16] style/addStyleMsg s form-urlencoded...")
result = make_request("POST", "/style/addStyleMsg", form_data)
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:300]}")
