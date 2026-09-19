#!/usr/bin/env python3
"""Ziskaj detailnu strukturu sablony 146."""
import json, urllib.request, urllib.parse

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def parse_response(raw):
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith('"') and text.endswith('"'):
        inner = text[1:-1].replace('\\"', '"')
        return json.loads(inner)
    return json.loads(text)

# Ziskaj orderJson pre style 146
print("[1] Ziskujem orderJson pre style 146...")
req = urllib.request.Request(f"{ESL_BASE}/style/getDispMsData?id=146")
req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
req.add_header("X-Requested-With", "XMLHttpRequest")
with urllib.request.urlopen(req, timeout=15) as resp:
    raw = resp.read()
    order_json = parse_response(raw)

print(f"    Pocet polov: {len(order_json)}")
print(f"\n=== PRVE 3 POLA ===")
for i, field in enumerate(order_json[:3]):
    print(f"\n  Pola {i}:")
    print(json.dumps(field, indent=4, ensure_ascii=False))

print(f"\n=== VSETKY KLUCE V PRVOM POLI ===")
if order_json:
    print(json.dumps(list(order_json[0].keys()), indent=2))
    if "style" in order_json[0]:
        print(f"\n=== STYLE KLUCY ===")
        print(json.dumps(list(order_json[0]["style"].keys()), indent=2))
