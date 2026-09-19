#!/usr/bin/env python3
"""Test updateStyle - skusam JSON body namiesto form-urlencoded."""
import json, urllib.request, urllib.parse

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def raw_request(method, path, body=None, content_type="application/x-www-form-urlencoded"):
    url = f"{ESL_BASE}{path}"
    
    req = urllib.request.Request(url, method=method)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    if body:
        req.add_header("Content-Type", content_type)
        if isinstance(body, str):
            body = body.encode("utf-8")
        req.data = body
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return {"status": resp.status, "raw": raw, "text": raw.decode("utf-8", errors="replace"), "length": len(raw)}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return {"status": e.code, "raw": raw, "text": raw.decode("utf-8", errors="replace"), "length": len(raw)}

# 1. Ziskaj orderJson
print("[1] Ziskujem orderJson...")
resp = raw_request("POST", "/style/getDispMsData", body="id=146")
text = resp['text'].strip()
if text.startswith('"') and text.endswith('"'):
    inner = text[1:-1].replace('\\"', '"')
    order_json = json.loads(inner)
else:
    order_json = json.loads(text)

print(f"    Pocet polov: {len(order_json)}")

# 2. Zmen farby
for f in order_json:
    if isinstance(f, dict) and f.get("type") == "text":
        f["style"]["color"] = "#ff0000"

# 3. Skusam JSON body
print("\n[2] Skusam JSON body...")
json_body = json.dumps({"id": 146, "orderJson": order_json}, ensure_ascii=False)
resp = raw_request("POST", "/style/updateDispMData", body=json_body, content_type="application/json")
print(f"    Status: {resp['status']}, Length: {resp['length']}, Text: {repr(resp['text'][:200])}")

# 4. Over
print("\n[3] Overujem...")
resp2 = raw_request("POST", "/style/getDispMsData", body="id=146")
text2 = resp2['text'].strip()
if text2.startswith('"') and text2.endswith('"'):
    inner2 = text2[1:-1].replace('\\"', '"')
    verify = json.loads(inner2)
else:
    verify = json.loads(text2)

red = sum(1 for f in verify if isinstance(f, dict) and f.get("type") == "text" and f.get("style", {}).get("color") == "#ff0000")
print(f"    Cervene: {red}/{len(verify)}")

# 5. Skusam JSON body s inym endpointom
print("\n[4] Skusam /style/updateStyle...")
json_body2 = json.dumps({"id": 146, "orderJson": order_json}, ensure_ascii=False)
resp3 = raw_request("POST", "/style/updateStyle", body=json_body2, content_type="application/json")
print(f"    Status: {resp3['status']}, Length: {resp3['length']}, Text: {repr(resp3['text'][:200])}")

# 6. Skusam JSON body s endpointom /style/update
print("\n[5] Skusam /style/update...")
resp4 = raw_request("POST", "/style/update", body=json_body2, content_type="application/json")
print(f"    Status: {resp4['status']}, Length: {resp4['length']}, Text: {repr(resp4['text'][:200])}")

# 7. Skusam JSON body s endpointom /style/save
print("\n[6] Skusam /style/save...")
resp5 = raw_request("POST", "/style/save", body=json_body2, content_type="application/json")
print(f"    Status: {resp5['status']}, Length: {resp5['length']}, Text: {repr(resp5['text'][:200])}")

# 8. Skusam JSON body s endpointom /style/updateDispMs
print("\n[7] Skusam /style/updateDispMs...")
resp6 = raw_request("POST", "/style/updateDispMs", body=json_body2, content_type="application/json")
print(f"    Status: {resp6['status']}, Length: {resp6['length']}, Text: {repr(resp6['text'][:200])}")
