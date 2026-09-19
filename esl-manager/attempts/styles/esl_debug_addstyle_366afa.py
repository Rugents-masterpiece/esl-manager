#!/usr/bin/env python3
"""Debug addStyle endpoint - presny format."""
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

# 2. Analyzuju style.js pre addStyle
print("\n[2] Analyzuju style.js pre addStyle...")
with urllib.request.urlopen(f"{ESL_BASE}/app/js/style.js", timeout=15) as resp:
    style_js = resp.read().decode("utf-8", errors="replace")

# Hladaj addStyle funkciu
idx = style_js.find("addStyle")
if idx > 0:
    print(f"    NASHIEL addStyle na pozicii {idx}")
    # Zober 2000 znakov okolo
    snippet = style_js[max(0,idx-200):idx+2000]
    print(f"    Kontext:\n{snippet}")

# 3. Skus addStyle s JSON a id parametrom
print("\n[3] addStyle s JSON body a id...")
create_json = json.dumps({
    "id": 9999,
    "name": "Klon_146_Test",
    "type": "1",
    "descriptor": "Template_Klon",
    "rotate": "0",
    "sid": "1"
}, ensure_ascii=False)
result = make_request("POST", "/style/addStyle", create_json, "application/json")
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")

# 4. Skus addStyle s JSON bez id
print("\n[4] addStyle s JSON bez id...")
create_json2 = json.dumps({
    "name": "Klon_146_Test2",
    "type": "1",
    "descriptor": "Template_Klon2",
    "rotate": "0",
    "sid": "1"
}, ensure_ascii=False)
result = make_request("POST", "/style/addStyle", create_json2, "application/json")
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")

# 5. Skus addStyle s JSON a parametrom id v URL
print("\n[5] addStyle s JSON body a ?id=9998...")
create_json3 = json.dumps({
    "name": "Klon_146_Test3",
    "type": "1",
    "descriptor": "Template_Klon3",
    "rotate": "0",
    "sid": "1"
}, ensure_ascii=False)
result = make_request("POST", "/style/addStyle?id=9998", create_json3, "application/json")
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")

# 6. Ziskaj vsetky style
print("\n[6] Ziskam vsetky style...")
result = make_request("GET", "/associate/getStyleMsgs", {"currentPage": "0", "pageSize": "200"})
raw = result['text_full']
try:
    styles = json.loads(raw)
    print(f"    Pocet stylistiek: {len(styles.get('datalist', []))}")
    max_id = 0
    for s in styles.get('datalist', []):
        sid = s.get('id', 0)
        if sid > max_id:
            max_id = sid
        print(f"      ID {sid}: {s.get('name', '?')}")
    print(f"    Najvyssie ID: {max_id}")
except:
    print(f"    Nemozem parsovat: {raw[:300]}")

# 7. Skus addStyle s JSON a body ako form-urlencoded s klucom "data"
print("\n[7] addStyle s form-urlencoded data=data...")
form_data = {
    "data": create_json2
}
result = make_request("POST", "/style/addStyle", form_data)
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")

# 8. Skus addStyle s form-urlencoded data=data a id
print("\n[8] addStyle s form-urlencoded data=data a id=9997...")
form_data2 = {
    "id": "9997",
    "data": create_json2
}
result = make_request("POST", "/style/addStyle", form_data2)
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")

# 9. Skus queryStyles
print("\n[9] queryStyles...")
result = make_request("GET", "/style/queryStyles", {"currentPage": "0", "pageSize": "5"})
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")

# 10. Skus getStyleData
print("\n[10] getStyleData...")
result = make_request("GET", "/style/getStyleData", {"id": "146"})
print(f"    Status: {result['status']}")
print(f"    Response: {result['text'][:500]}")
