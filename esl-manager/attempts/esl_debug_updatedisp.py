#!/usr/bin/env python3
"""Debug updateDispMData - presny format requestu a response."""
import json, urllib.request, urllib.parse, hashlib, http.cookiejar, copy

ESL_BASE = "http://192.168.16.251/esls_new"

def make_request(method, path, data=None, content_type="application/x-www-form-urlencoded; charset=UTF-8"):
    """Urobi request a vrati detailne info."""
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
            status = resp.status
            headers = dict(resp.headers)
            cookies = [c.name + "=" + c.value for c in cj]
            return {
                "status": status,
                "headers": headers,
                "cookies": cookies,
                "raw_length": len(raw),
                "text": text[:500],
                "text_full": text,
            }
    except urllib.error.HTTPError as e:
        raw = e.read()
        text = raw.decode("utf-8", errors="replace").strip()
        return {
            "status": e.code,
            "headers": dict(e.headers),
            "cookies": [c.name + "=" + c.value for c in cj],
            "raw_length": len(raw),
            "text": text[:500],
            "text_full": text,
            "error": True,
        }

# 1. Login
print("[1] Login...")
passwd_md5 = hashlib.md5(b"admin").hexdigest()
login_data = {"username": "admin", "passwd": passwd_md5}
result = make_request("POST", "/login/userLogin", login_data)
print(f"    Status: {result['status']}")
print(f"    Cookies: {result['cookies']}")
session_id = None
for c in result['cookies']:
    if "JSESSIONID" in c:
        session_id = c.split("=")[1]
        break
print(f"    Session: {session_id}")

# 2. Ziskaj data zo style 146
print("\n[2] Ziskam data zo style 146...")
disp_data = make_request("POST", "/style/getDispMsData", {"id": "146"})
print(f"    Status: {disp_data['status']}")
print(f"    Response: {disp_data['text'][:300]}")

# Parse
raw_text = disp_data['text_full']
order_json = None
if raw_text.startswith('"') and raw_text.endswith('"'):
    inner = raw_text[1:-1].replace('\\"', '"')
    try:
        order_json = json.loads(inner)
    except:
        pass
elif raw_text.startswith('['):
    try:
        order_json = json.loads(raw_text)
    except:
        pass

if order_json and isinstance(order_json, list):
    print(f"    Pocet polov: {len(order_json)}")
    for i, field in enumerate(order_json):
        if isinstance(field, dict):
            print(f"      [{i}] {field.get('mpname', field.get('name', '?'))}: {json.dumps(field, ensure_ascii=False)[:200]}")
else:
    print(f"    Nemozem parsovat: {type(raw_text)} - {raw_text[:200]}")

# 3. Vytvor novu sablonu s novym ID
print("\n[3] Vytvorim novu sablonu...")
new_id = 9999  # Skusme velke ID
create_data = {
    "id": str(new_id),
    "name": "Klon_146",
    "type": "1",
    "descriptor": "Template9999",
    "rotate": "0",
    "sid": "1"
}
result = make_request("POST", "/style/addStyle", create_data)
print(f"    Status: {result['status']}")
print(f"    Response: {result['text']}")

# 4. Skus updateDispMData s form-urlencoded
print("\n[4] updateDispMData s form-urlencoded...")
if order_json and isinstance(order_json, list):
    json_str = json.dumps(order_json, ensure_ascii=False)
    form_data = {
        "id": str(new_id),
        "orderJson": json_str
    }
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")
    
    # Over ci sa ulozilo
    print("\n[5] Overenie - getDispMsData pre ID {new_id}...")
    verify = make_request("POST", "/style/getDispMsData", {"id": str(new_id)})
    print(f"    Status: {verify['status']}")
    print(f"    Response: {verify['text'][:300]}")
    
    # Skus aj getStyleMsgById
    print(f"\n[6] getStyleMsgById pre ID {new_id}...")
    verify2 = make_request("POST", "/style/getStyleMsgById", {"id": str(new_id)})
    print(f"    Status: {verify2['status']}")
    print(f"    Response: {verify2['text'][:300]}")

# 7. Skus updateDispMData s JSON body
print("\n[7] updateDispMData s JSON body...")
if order_json and isinstance(order_json, list):
    json_body = json.dumps({"id": new_id, "orderJson": order_json}, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData", json_body, "application/json")
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 8. Skus updateDispMData s presnymi parametrami z JS
print("\n[8] Skusim presny format z JS...")
if order_json and isinstance(order_json, list):
    # Z tag.js vidim ze sa pouziva ajaxSubmit s contentType: 'application/json'
    # a data: $('#modifyTagForm').serialize()
    # To znamena ze aj ked contentType je JSON, data su form-encoded
    
    # Skusme s parametrom id v URL
    json_str = json.dumps(order_json, ensure_ascii=False)
    result = make_request("POST", "/style/updateDispMData?id=" + str(new_id), {"orderJson": json_str})
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")

# 9. Skus updateDispMData na original style 146
print("\n[9] updateDispMData na original style 146...")
if order_json and isinstance(order_json, list):
    json_str = json.dumps(order_json, ensure_ascii=False)
    form_data = {
        "id": "146",
        "orderJson": json_str
    }
    result = make_request("POST", "/style/updateDispMData", form_data)
    print(f"    Status: {result['status']}")
    print(f"    Response: {result['text'][:300]}")
    
    # Over - zmenime jedno pole a uvidime
    print("\n[10] Zmenim jedno pole v 146 a otestujem...")
    modified = copy.deepcopy(order_json)
    if modified and len(modified) > 0:
        modified[0]["mpname"] = "TEST_CHANGED_" + str(new_id)
        json_str2 = json.dumps(modified, ensure_ascii=False)
        form_data2 = {
            "id": "146",
            "orderJson": json_str2
        }
        result2 = make_request("POST", "/style/updateDispMData", form_data2)
        print(f"    Status: {result2['status']}")
        print(f"    Response: {result2['text'][:300]}")
        
        # Over
        print("\n[11] Overenie zmeny v 146...")
        verify3 = make_request("POST", "/style/getDispMsData", {"id": "146"})
        print(f"    Status: {verify3['status']}")
        print(f"    Response: {verify3['text'][:300]}")
