#!/usr/bin/env python3
"""Test skript pre všetky ESL API endpointy — vrátane nových z component.js."""

import json
import urllib.request
import urllib.parse
import sys

BASE_URL = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"
TIMEOUT = 15

def make_request(method, path, params=None, body=None, content_type=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    req = urllib.request.Request(url, method=method)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    req.add_header("Accept", "*/*")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    
    if content_type:
        req.add_header("Content-Type", content_type)
    if body:
        if isinstance(body, str):
            body = body.encode("utf-8")
        req.data = body
    
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            status = resp.status
            ct = resp.headers.get("Content-Type", "")
            text = data[:500].decode("utf-8", errors="replace")
            if len(text) > 500:
                text += "..."
            print(f"  {method} {path} -> {status} | {ct} | {len(data)}b")
            print(f"  Response: {text}")
            return {"status": status, "data": data}
    except urllib.error.HTTPError as e:
        err = e.read()
        print(f"  {method} {path} -> {e.code} ERROR")
        text = err[:300].decode("utf-8", errors="replace")
        print(f"  Error: {text}")
        return {"status": e.code, "error": True}
    except Exception as e:
        print(f"  {method} {path} -> EXC: {e}")
        return {"error": str(e)}


print("TESTING ALL ESL API ENDPOINTS")
print("="*60)

results = {}

# === EXISTING ENDPOINTS ===
print("\n--- Existing endpoints ---")
r = make_request("GET", "/associate/getTagsMsg")
results["getTagsMsg"] = r

r = make_request("GET", "/associate/getStylesMsg")
results["getStylesMsg"] = r

r = make_request("GET", "/associate/getStyleMsgs", params={"currentPage": 0, "pageSize": 5})
results["getStyleMsgs"] = r

r = make_request("POST", "/associate/getStyleMsgById", params={"id": 146})
results["getStyleMsgById"] = r

r = make_request("GET", "/style/getDispMs", params={"id": 146})
results["getDispMs"] = r

r = make_request("GET", "/associate/getPhotos")
results["getPhotos"] = r

r = make_request("GET", "/associate/getPhotoDataByName", params={"photoName": "bg1"})
results["getPhotoDataByName"] = r

r = make_request("GET", "/bg1.png")
results["raw_image"] = r

r = make_request("POST", "/associate/updateScreen", body=json.dumps([{
    "mac": "92.91.87.80", "styleid": 146, "mappingtype": 1, "ABDisplayFlag": 163,
    "Name": "Test", "PriceRetail": "9.99"
}]).encode("utf-8"), content_type="application/json")
results["updateScreen"] = r

# === NEW ENDPOINTS from component.js ===
print("\n--- NEW endpoints from component.js ---")

# 1. style/getPhotoName
r = make_request("POST", "/style/getPhotoName", params={"stylealignId": 2, "styleid": 146}, body=b"{}", content_type="application/json")
results["getPhotoName"] = r

# 2. style/getBgMsg
r = make_request("POST", "/style/getBgMsg", params={"stylealignId": 2}, body=b"{}", content_type="application/json")
results["getBgMsg"] = r

# 3. style/getBgImg
r = make_request("POST", "/style/getBgImg", params={"ImgId": 50}, body=b"{}", content_type="application/json")
results["getBgImg"] = r

# 4. style/removeBackground
r = make_request("POST", "/style/removeBackground", params={"mappingtype": 1, "styleid": 146}, body=b"{}", content_type="application/json")
results["removeBackground"] = r

# 5. style/addColumnAndGood
r = make_request("POST", "/style/addColumnAndGood", params={
    "columnName": "text", "mappingText": "TestColumn", "mappingtype": 1, "styleid": 146
}, body=b"{}", content_type="application/json")
results["addColumnAndGood"] = r

# 6. mms/updateDispMData (the one that works!)
style_data = make_request("POST", "/associate/getStyleMsgById", params={"id": 146})
if style_data["status"] == 200:
    try:
        sj = json.loads(style_data["data"].decode("utf-8"))
        fields = sj["datalist"][0]["styleFileds"]
        order = []
        for f in fields:
            order.append({
                "mpname": f, "prefix": "", "name": f.lower(),
                "style": {"z-index":0,"color":"#000","font-weight":400,"font-size":"13px","background-color":"#fff","board-width":"1px","top":"2px","left":"1px","width":"290px","font-family":"HuaweiSans-Light","height":"50px","text-align":"left","autoReacting":False},
                "id": str(abs(hash(f))%10000), "text": f"Test {f}", "type": "text",
                "suffix": "", "feil": "text", "table": "tb_tagsandgoods", "status": True
            })
        r = make_request("POST", "/mms/updateDispMData", params={"id": 146}, body=json.dumps({"orderJson": order}).encode("utf-8"), content_type="application/json")
        results["updateDispMData"] = r
    except Exception as e:
        results["updateDispMData"] = {"error": str(e)}

# 7. style/updateStyleAlign
r = make_request("POST", "/style/updateStyleAlign", params={"styleid": 146, "stylealign": 2, "styleName": "S29BasePriceTag_V1"}, body=b"{}", content_type="application/json")
results["updateStyleAlign"] = r

# 8. style/uploadPhoto (form data)
r = make_request("POST", "/style/uploadPhoto", body=b"test", content_type="multipart/form-data")
results["uploadPhoto"] = r

# 9. style/getDispMsData (NEW!)
r = make_request("POST", "/style/getDispMsData", params={"id": 146}, body=b"{}", content_type="application/json")
results["getDispMsData"] = r

# 10. style/delDismp
r = make_request("POST", "/style/delDismp", params={"styleid": 146}, body=b"{}", content_type="application/json")
results["delDismp"] = r

# 11. style/previewImg
r = make_request("POST", "/style/previewImg", params={"id": 146}, body=b"{}", content_type="application/json")
results["previewImg"] = r

# 12. mms/uploadFont
r = make_request("POST", "/mms/uploadFont", params={"filePath": "/usr/share/fonts/", "fontName": "test.ttf"}, body=b"{}", content_type="application/json")
results["uploadFont"] = r

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