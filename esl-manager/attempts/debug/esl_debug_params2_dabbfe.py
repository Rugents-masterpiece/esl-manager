#!/usr/bin/env python3
"""Skus tag/updateTag format pre style."""
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

# 3. Skus style/updateDispMData s contentType application/json
print("\n[3] style/updateDispMData s contentType application/json...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")
    
    # Over
    print("\n[4] Overenie...")
    verify = make_request("POST", "/style/getDispMsData", {"id": "146"})
    vraw = verify['text_full']
    if vraw.startswith('"') and vraw.endswith('"'):
        vinner = vraw[1:-1].replace('\\"', '"')
        try:
            vdata = json.loads(vinner)
            print(f"    Prve pole: {vdata[0].get('mpname', '?') if vdata else 'empty'}")
        except:
            print(f"    Nemozem parsovat: {vraw[:200]}")

# 5. Skus style/updateDispMData s contentType application/json a id v URL
print("\n[5] style/updateDispMData s contentType application/json a id v URL...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps(order_json, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData?id=146", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 6. Skus style/updateDispMData s contentType application/json a id v JSON
print("\n[6] style/updateDispMData s contentType application/json a id v JSON...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "data": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 7. Skus style/updateDispMData s contentType application/json a fields
print("\n[7] style/updateDispMData s contentType application/json a fields...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "fields": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 8. Skus style/updateDispMData s contentType application/json a order
print("\n[8] style/updateDispMData s contentType application/json a order...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "order": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 9. Skus style/updateDispMData s contentType application/json a style
print("\n[9] style/updateDispMData s contentType application/json a style...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "style": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 10. Skus style/updateDispMData s contentType application/json a disp
print("\n[10] style/updateDispMData s contentType application/json a disp...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "disp": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 11. Skus style/updateDispMData s contentType application/json a content
print("\n[11] style/updateDispMData s contentType application/json a content...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "content": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 12. Skus style/updateDispMData s contentType application/json a body
print("\n[12] style/updateDispMData s contentType application/json a body...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "body": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 13. Skus style/updateDispMData s contentType application/json a value
print("\n[13] style/updateDispMData s contentType application/json a value...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "value": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 14. Skus style/updateDispMData s contentType application/json a param
print("\n[14] style/updateDispMData s contentType application/json a param...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "param": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 15. Skus style/updateDispMData s contentType application/json a config
print("\n[15] style/updateDispMData s contentType application/json a config...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "config": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 16. Skus style/updateDispMData s contentType application/json a settings
print("\n[16] style/updateDispMData s contentType application/json a settings...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "settings": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 17. Skus style/updateDispMData s contentType application/json a options
print("\n[17] style/updateDispMData s contentType application/json a options...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "options": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 18. Skus style/updateDispMData s contentType application/json a preferences
print("\n[18] style/updateDispMData s contentType application/json a preferences...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "preferences": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 19. Skus style/updateDispMData s contentType application/json a choices
print("\n[19] style/updateDispMData s contentType application/json a choices...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "choices": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 20. Skus style/updateDispMData s contentType application/json a selections
print("\n[20] style/updateDispMData s contentType application/json a selections...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": 146, "selections": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")
