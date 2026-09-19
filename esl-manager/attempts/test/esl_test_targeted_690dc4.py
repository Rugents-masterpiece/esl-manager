#!/usr/bin/env python3
"""Targeted test for failing endpoints."""

import json
import urllib.request
import urllib.parse

BASE_URL = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def test(method, path, params=None, body=None, content_type=None, headers=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    req = urllib.request.Request(url, method=method)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("Accept", "*/*")
    
    if content_type:
        req.add_header("Content-Type", content_type)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if body:
        if isinstance(body, str):
            body = body.encode("utf-8")
        req.data = body
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            print(f"OK: {method} {path} -> {resp.status}")
            text = data[:500].decode("utf-8", errors="replace")
            print(f"  Response: {text}")
            return {"status": resp.status, "data": data}
    except urllib.error.HTTPError as e:
        err = e.read()
        print(f"FAIL: {method} {path} -> {e.code}")
        text = err[:300].decode("utf-8", errors="replace")
        print(f"  Error: {text}")
        return {"status": e.code, "error": True}
    except Exception as e:
        print(f"EXC: {method} {path} -> {e}")
        return {"error": str(e)}

print("TARGETED TESTS")
print("="*60)

# Test 1: updateDispMData with JSON body (not form data)
style_data = test("POST", "/associate/getStyleMsgById", params={"id": 146})
if style_data["status"] == 200:
    try:
        sj = json.loads(style_data["data"].decode("utf-8"))
        fields = sj["datalist"][0]["styleFileds"]
        order = []
        for f in fields:
            order.append({
                "mpname": f,
                "prefix": "",
                "name": f.lower(),
                "style": {"z-index":0,"color":"#000","font-weight":400,"font-size":"13px","background-color":"#fff","board-width":"1px","top":"2px","left":"1px","width":"290px","font-family":"HuaweiSans-Light","height":"50px","text-align":"left","autoReacting":False},
                "id": str(hash(f)%10000),
                "text": f"Test {f}",
                "type": "text",
                "suffix": "",
                "feil": "text",
                "table": "tb_tagsandgoods",
                "status": True
            })
        
        # Try as JSON body
        print("\n--- Test: updateDispMData as JSON body ---")
        r = test("POST", "/style/updateDispMData", params={"id": 146}, 
                 body=json.dumps({"orderJson": order}), 
                 content_type="application/json")
        
        # Try as form data with orderJson as single field
        print("\n--- Test: updateDispMData form data, orderJson as single field ---")
        r2 = test("POST", "/style/updateDispMData", params={"id": 146},
                  body=urllib.parse.urlencode({"id": "146", "orderJson": json.dumps(order)}).encode("utf-8"),
                  content_type="application/x-www-form-urlencoded")
    except Exception as e:
        print(f"Parse error: {e}")

# Test 2: getRoutersMsg - try with different approaches
print("\n--- Test: getRoutersMsg ---")
test("GET", "/associate/getRoutersMsg")

# Try with params
print("\n--- Test: getRoutersMsg with params ---")
test("GET", "/associate/getRoutersMsg", params={"currentPage": 0, "pageSize": 10})

# Try POST
print("\n--- Test: getRoutersMsg as POST ---")
test("POST", "/associate/getRoutersMsg", body=b"{}", content_type="application/json")

# Test 3: getDispMs - try different approach
print("\n--- Test: getDispMs ---")
test("GET", "/style/getDispMs", params={"id": 146})

# Try with different path format
print("\n--- Test: getDispMs as POST ---")
test("POST", "/style/getDispMs", params={"id": 146}, body=b"", content_type="application/x-www-form-urlencoded")

print("\nDone.")