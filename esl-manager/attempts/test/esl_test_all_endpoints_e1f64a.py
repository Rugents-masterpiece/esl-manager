#!/usr/bin/env python3
"""Skusam najst endpoint pre vytvorenie novej sablony."""
import json, urllib.request, urllib.parse

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

# Ziskaj orderJson zo style 146
print("[1] Ziskujem orderJson zo style 146...")
req = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
with urllib.request.urlopen(req, timeout=15) as resp:
    raw = resp.read()
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith('"') and text.endswith('"'):
        inner = text[1:-1].replace('\\"', '"')
        order_json = json.loads(inner)
    else:
        order_json = json.loads(text)
    
    print(f"  Pocet polov: {len(order_json)}")

# Zmen farby na cervenu
for f in order_json:
    if f.get("type") == "text":
        f["style"]["color"] = "#ff0000"

# Skusam endpointy s inymi parametrami
endpoints_to_try = [
    ("/style/create", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/new", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/insert", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/save", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/add", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/createNew", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/createStyle", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/saveStyle", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/addStyle", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/createTemplate", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/saveTemplate", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/addTemplate", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/createDispMs", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/saveDispMs", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
    ("/style/addDispMs", {"styleName": "Kopia_Rudo_Cervena", "orderJson": json.dumps(order_json, ensure_ascii=False)}),
]

for endpoint, params in endpoints_to_try:
    print(f"\n[Testing {endpoint}]")
    body = urllib.parse.urlencode(params, encoding="utf-8").encode("utf-8")
    
    req = urllib.request.Request(
        f"{ESL_BASE}{endpoint}",
        data=body,
        method="POST"
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            ct = resp.headers.get("Content-Type", "unknown")
            status = resp.status
            print(f"  Status: {status}, Content-Type: {ct}, Length: {len(data)}")
            print(f"  Raw: {repr(data[:200])}")
            
            # Skontroluj ci sa nova sablona vytvorila
            if status == 200 and len(data) > 0:
                print(f"  *** POTENCIÁLNY ÚSPECH! Skontrolujem zoznam sablón...")
                req2 = urllib.request.Request(f"{ESL_BASE}/associate/getStylesMsg")
                req2.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
                with urllib.request.urlopen(req2, timeout=15) as resp2:
                    raw2 = resp2.read()
                    text2 = raw2.decode("utf-8", errors="replace").strip()
                    if text2.startswith('"') and text2.endswith('"'):
                        inner2 = text2[1:-1].replace('\\"', '"')
                        styles2 = json.loads(inner2)
                    else:
                        styles2 = json.loads(text2)
                    
                    found = [s for s in styles2 if "Kopia" in s.get("name", "")]
                    if found:
                        print(f"  *** Nájdená nová šablóna: {found[0]}")
                        break
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {body_err[:100]}")
    except Exception as e:
        print(f"  Error: {e}")
