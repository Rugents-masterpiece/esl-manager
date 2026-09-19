#!/usr/bin/env python3
"""Test: updateDispMData s ID 146 - zmena farby a mena."""

import json
import urllib.request
import urllib.parse

BASE_URL = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def test(method, path, params=None, body=None, content_type=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method=method)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("Accept", "*/*")
    if content_type:
        req.add_header("Content-Type", content_type)
    if body:
        if isinstance(body, str):
            body = body.encode("utf-8")
        req.data = body
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            text = data[:300].decode("utf-8", errors="replace")
            print(f"OK {resp.status}: {method} {path}")
            print(f"  Response: {text}")
            return {"status": resp.status, "data": data}
    except urllib.error.HTTPError as e:
        err = e.read()
        text = err[:300].decode("utf-8", errors="replace")
        print(f"FAIL {e.code}: {method} {path}")
        print(f"  Error: {text}")
        return {"status": e.code, "error": True}

# Get template structure
r = test("POST", "/associate/getStyleMsgById", params={"id": 146})
sj = json.loads(r["data"].decode("utf-8"))
template = sj["datalist"][0]
fields = template["styleFileds"]

print(f"Template: {template['name']} (ID={template['id']})")
print(f"Fields: {fields}")

# Create orderJson with CHANGED colors and name
order = []
for f in fields:
    order.append({
        "mpname": f,
        "prefix": "",
        "name": f.lower(),
        "style": {
            "z-index": 0,
            "color": "#ff0000",  # ZMENENA FARBA TEXTU
            "font-weight": 700,
            "text-decoration": "none",
            "font-size": "13px",
            "background-color": "#ffff00",  # ZMENENA FARBA POZADIA
            "board-width": "1px",
            "top": "2px",
            "left": "1px",
            "width": "290px",
            "font-family": "HuaweiSans-Light",
            "height": "50px",
            "text-align": "left",
            "autoReacting": False
        },
        "id": str(hash(f)%10000),
        "text": f"NOVY_NAZOV_{f}",  # ZMENENA MENO
        "type": "text",
        "suffix": "",
        "feil": "text",
        "table": "tb_tagsandgoods",
        "status": True
    })

print(f"\nSending updateDispMData with {len(order)} fields (changed colors and names)")
r = test("POST", "/style/updateDispMData", params={"id": 146},
         body=urllib.parse.urlencode({"id": "146", "orderJson": json.dumps(order)}).encode("utf-8"),
         content_type="application/x-www-form-urlencoded")

if r["status"] == 200:
    print("\nSUCCESS! Template updated!")
elif r["status"] == 500:
    print("\nNPE but data passed (as expected)")
    # Verify - get the updated template
    r2 = test("POST", "/associate/getStyleMsgById", params={"id": 146})
    if r2["status"] == 200:
        sj2 = json.loads(r2["data"].decode("utf-8"))
        t2 = sj2["datalist"][0]
        print(f"Updated template: {t2['name']}")
        print(f"Fields: {t2['styleFileds']}")
        # Check if text changed
        for field in t2.get("styleFileds", []):
            print(f"  {field}")