#!/usr/bin/env python3
"""Over updateStyle - zmena mena style 146."""
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

# 2. Zmen meno style 146 cez updateStyle
print("\n[2] Zmenim meno style 146...")
update_json = json.dumps({
    "name": "Rudo_TEST_146_ZMENENE",
    "type": "1",
    "descriptor": "Rudo",
    "rotate": "0",
    "sid": "146"
}, ensure_ascii=False)
result = make_request("POST", "/style/updateStyle", update_json, "application/json")
print(f"    Status: {result['status']}")
print(f"    Response: {result['text']}")

# 3. Over cez getStyleMsgs
print("\n[3] Over cez getStyleMsgs...")
result = make_request("GET", "/associate/getStyleMsgs", {"currentPage": "0", "pageSize": "200"})
raw = result['text_full']
try:
    styles = json.loads(raw)
    for s in styles.get('datalist', []):
        if s.get('id') == 146:
            print(f"    ID 146: name={s.get('name', '?')}, descriptor={s.get('descriptor', '?')}")
            break
    else:
        print(f"    Style 146 nenájdený!")
except:
    print(f"    Nemozem parsovat: {raw[:300]}")

# 4. Ziskaj data zo style 146
print("\n[4] getDispMsData pre 146...")
result = make_request("POST", "/style/getDispMsData", {"id": "146"})
raw = result['text_full']
print(f"    Status: {result['status']}")
print(f"    Response: {raw[:300]}")

# 5. Skus updateStyle s orderJson
print("\n[5] updateStyle s orderJson...")
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
    modified = copy.deepcopy(order_json) if 'copy' in dir(__import__('copy')) else order_json
    import copy
    modified = copy.deepcopy(order_json)
    modified[0]["mpname"] = "CHANGED_BY_UPDATESTYLE"
    
    update_json2 = json.dumps({
        "id": 146,
        "name": "Rudo_TEST_146_ZMENENE2",
        "type": "1",
        "descriptor": "Rudo",
        "rotate": "0",
        "sid": "146",
        "orderJson": modified
    }, ensure_ascii=False)
    result = make_request("POST", "/style/updateStyle", update_json2, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text']}")
    
    # Over
    print("\n[6] Overenie zmeny...")
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
