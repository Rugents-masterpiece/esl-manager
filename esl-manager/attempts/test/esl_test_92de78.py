#!/usr/bin/env python3
"""Test skript pre ESL API - zavolá každý endpoint a loguje raw odpoveď."""

import json
import urllib.request
import urllib.parse
import sys
import os

BASE_URL = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"
TIMEOUT = 15

def make_request(method, path, params=None, form_data=None, body=None, content_type=None):
    """Generic request maker - loguje všetko."""
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    req = urllib.request.Request(url, method=method)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("Accept", "*/*")
    
    if content_type:
        req.add_header("Content-Type", content_type)
    if form_data:
        body = urllib.parse.urlencode(form_data).encode("utf-8")
    if body:
        req.data = body
    
    print(f"\n{'='*60}")
    print(f"METHOD: {method}")
    print(f"URL: {url}")
    if form_data:
        print(f"FORM DATA: {form_data}")
    if body and not form_data:
        print(f"BODY: {body[:200]}...")
    print(f"{'='*60}")
    
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            ct = resp.headers.get("Content-Type", "unknown")
            status = resp.status
            print(f"STATUS: {status}")
            print(f"CONTENT-TYPE: {ct}")
            print(f"LENGTH: {len(data)} bytes")
            
            # Show first 1000 chars
            text = data[:1000].decode("utf-8", errors="replace")
            if len(text) > 1000:
                text += f"\n... (truncated, total {len(data)} bytes)"
            print(f"RESPONSE:\n{text}")
            
            # Save full response
            resp_file = f"/tmp/esl_resp_{method}_{path.replace('/', '_').strip('_')}.txt"
            with open(resp_file, "w") as f:
                f.write(f"URL: {url}\nSTATUS: {status}\nCT: {ct}\n\n")
                f.write(data.decode("utf-8", errors="replace"))
            print(f"FULL RESPONSE saved: {resp_file}")
            
            return {"status": status, "ct": ct, "data": data}
    except urllib.error.HTTPError as e:
        err_data = e.read()
        print(f"HTTP ERROR: {e.code} - {e.reason}")
        print(f"BODY: {err_data[:500].decode('utf-8', errors='replace')}")
        resp_file = f"/tmp/esl_err_{method}_{path.replace('/', '_').strip('_')}.txt"
        with open(resp_file, "w") as f:
            f.write(f"URL: {url}\nERROR: {e.code} {e.reason}\n\n")
            f.write(err_data.decode("utf-8", errors="replace"))
        print(f"ERROR saved: {resp_file}")
        return {"status": e.code, "error": True}
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return {"error": str(e)}


print("TESTING ESL API ENDPOINTS")
print(f"Server: {BASE_URL}")
print(f"Session: {SESSION_ID}")
print(f"Python: {sys.version}")
print("="*60)

results = {}

# 1. GET /associate/getTagsMsg
r = make_request("GET", "/associate/getTagsMsg")
results["getTagsMsg"] = r

# 2. GET /associate/getStylesMsg
r = make_request("GET", "/associate/getStylesMsg")
results["getStylesMsg"] = r

# 3. GET /associate/getStyleMsgs (paginated)
r = make_request("GET", "/associate/getStyleMsgs", params={"currentPage": 0, "pageSize": 5})
results["getStyleMsgs"] = r

# 4. POST /associate/getStyleMsgById?id=146
r = make_request("POST", "/associate/getStyleMsgById", params={"id": 146})
results["getStyleMsgById"] = r

# 5. GET /style/getDispMs?id=146
r = make_request("GET", "/style/getDispMs", params={"id": 146})
results["getDispMs"] = r

# 6. POST /style/updateDispMData?id=146 (with minimal orderJson)
minimal_order = [{"mpname":"Test","name":"text1","text":"test","type":"text","status":True}]
r = make_request("POST", "/style/updateDispMData", params={"id": 146}, form_data={"id": "146", "orderJson": json.dumps(minimal_order)})
results["updateDispMData"] = r

# 7. GET /associate/getRoutersMsg
r = make_request("GET", "/associate/getRoutersMsg")
results["getRoutersMsg"] = r

# 8. GET /associate/getPhotos
r = make_request("GET", "/associate/getPhotos")
results["getPhotos"] = r

# 9. GET /associate/getPhotoDataByName?photoName=CiernoBielyPrvy132.png
r = make_request("GET", "/associate/getPhotoDataByName", params={"photoName": "CiernoBielyPrvy132.png"})
results["getPhotoDataByName"] = r

# 10. GET /CiernoBielyPrvy132.png (raw image URL)
r = make_request("GET", "/CiernoBielyPrvy132.png")
results["raw_image"] = r

# 11. POST /associate/updateScreen (minimal)
minimal_update = [{"mac": "92.91.87.80", "styleid": 146, "mappingtype": 1, "ABDisplayFlag": 163}]
r = make_request("POST", "/associate/updateScreen", body=json.dumps(minimal_update).encode("utf-8"), content_type="application/json")
results["updateScreen"] = r

# 12. POST /associate/delTagsByMac (minimal, with empty array)
r = make_request("POST", "/associate/delTagsByMac", body=json.dumps([]).encode("utf-8"), content_type="application/json")
results["delTagsByMac"] = r

# Summary
print("\n\n" + "="*60)
print("SUMMARY")
print("="*60)
for name, r in results.items():
    status = r.get("status", "N/A")
    has_error = r.get("error", False)
    if isinstance(has_error, bool) and has_error:
        print(f"  {name}: ERROR ({status})")
    else:
        print(f"  {name}: OK (status={status})")

print("\nAll responses saved to /tmp/esl_resp_*.txt and /tmp/esl_err_*.txt")