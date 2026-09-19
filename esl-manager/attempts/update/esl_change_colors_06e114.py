#!/usr/bin/env python3
"""Zmena farieb na cervenu pre style 146."""
import sys, json, urllib.request, urllib.parse

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def raw_post(path, params=None, form_data=None):
    url = f"{ESL_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    body = None
    if form_data:
        body = urllib.parse.urlencode(form_data, encoding="utf-8").encode("utf-8")
    
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            status = resp.status
            ct = resp.headers.get("Content-Type", "")
            text = raw.decode("utf-8", errors="replace").strip()
            return {"status": status, "content_type": ct, "raw": raw, "text": text, "length": len(raw)}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return {"status": e.code, "raw": raw, "text": raw.decode("utf-8", errors="replace"), "length": len(raw)}

# 1. Ziskaj orderJson zo style 146
print("[1] Ziskujem orderJson zo style 146...")
resp = raw_post("/style/getDispMsData", params={"id": "146"})
print(f"    Status: {resp['status']}, Length: {resp['length']}")
text = resp['text'].strip()
print(f"    First 200 chars: {repr(text[:200])}")

if text.startswith('"') and text.endswith('"'):
    inner = text[1:-1].replace('\\"', '"')
    order_json = json.loads(inner)
elif text.startswith('['):
    order_json = json.loads(text)
else:
    print(f"    ERROR: Nepodarilo sa parsovat orderJson. Text: {repr(text[:300])}")
    sys.exit(1)

print(f"    Pocet polov: {len(order_json)}")
for f in order_json:
    if isinstance(f, dict):
        color = f.get("style", {}).get("color", "N/A")
        print(f"      - {f.get('mpname', '?')}: '{f.get('text', '')[:30]}' farba={color}")

# 2. Zmen vsetky texty na cervenu
print("\n[2] Menim farby na cervenu (#ff0000)...")
changed = 0
for field in order_json:
    if isinstance(field, dict) and field.get("type") == "text":
        style_obj = field.get("style", {})
        if style_obj:
            old_color = style_obj.get("color", "N/A")
            style_obj["color"] = "#ff0000"
            field["style"] = style_obj
            changed += 1

print(f"    Zmenenych polov: {changed}")

# 3. Aktualizuj style - skusam viac sposobov
print("\n[3] Aktualizujem style 146...")

# Sposob 1: updateDispMData s id v params aj v body
print("    Sposob 1: updateDispMData (id v params + body)...")
json_str = json.dumps(order_json, ensure_ascii=False)
resp1 = raw_post("/style/updateDispMData", params={"id": "146"}, form_data={"id": "146", "orderJson": json_str})
print(f"      Status: {resp1['status']}, Length: {resp1['length']}, Text: {repr(resp1['text'][:100])}")

# Sposob 2: updateDispMData len v body
print("    Sposob 2: updateDispMData (len v body)...")
resp2 = raw_post("/style/updateDispMData", form_data={"id": "146", "orderJson": json_str})
print(f"      Status: {resp2['status']}, Length: {resp2['length']}, Text: {repr(resp2['text'][:100])}")

# Sposob 3: updateDispMData s id len v params
print("    Sposob 3: updateDispMData (id len v params)...")
resp3 = raw_post("/style/updateDispMData", params={"id": "146", "orderJson": json_str})
print(f"      Status: {resp3['status']}, Length: {resp3['length']}, Text: {repr(resp3['text'][:100])}")

# 4. Over ci sa zmeny ulozili
print("\n[4] Overujem ci sa zmeny ulozili...")
resp_verify = raw_post("/style/getDispMsData", params={"id": "146"})
text_verify = resp_verify['text'].strip()

if text_verify.startswith('"') and text_verify.endswith('"'):
    inner = text_verify[1:-1].replace('\\"', '"')
    verify_json = json.loads(inner)
elif text_verify.startswith('['):
    verify_json = json.loads(text_verify)
else:
    print(f"    ERROR: Nepodarilo sa overit. Text: {repr(text_verify[:300])}")
    sys.exit(1)

red_count = 0
for f in verify_json:
    if isinstance(f, dict) and f.get("type") == "text":
        color = f.get("style", {}).get("color", "N/A")
        if color == "#ff0000":
            red_count += 1

print(f"    Pocet cervenych polov: {red_count}/{len(verify_json)}")
if red_count == len(verify_json):
    print("    *** VSETKY POLA SU CERVENE! ***")
else:
    print(f"    *** ZLYHANIE - len {red_count}/{len(verify_json)} cervenych ***")
    for f in verify_json:
        if isinstance(f, dict):
            color = f.get("style", {}).get("color", "N/A")
            print(f"      - {f.get('mpname', '?')}: {color}")
