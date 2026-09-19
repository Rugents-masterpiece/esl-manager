#!/usr/bin/env python3
"""Stiahne a analyzuje JS súbory z ESL dashboardu."""
import json, urllib.request, urllib.parse

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def raw_get(path):
    url = f"{ESL_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"ERROR: {e}"

# 1. Skusam najst JS subory
print("[1] Skusam najst JS subory...")
js_paths = [
    "/esls_new/js/app.js",
    "/esls_new/js/main.js",
    "/esls_new/js/index.js",
    "/esls_new/js/api.js",
    "/esls_new/js/style.js",
    "/esls_new/js/update.js",
    "/esls_new/js/esl.js",
    "/esls_new/js/dashboard.js",
    "/esls_new/js/controller.js",
    "/esls_new/js/service.js",
    "/esls_new/js/updateDispMData.js",
    "/esls_new/js/updateStyle.js",
    "/esls_new/js/updateDispMs.js",
    "/esls_new/js/updateDispMData.js",
]

for path in js_paths:
    result = raw_get(path)
    if not result.startswith("ERROR"):
        print(f"    FOUND: {path} ({len(result)} chars)")
        # Hladam updateDispMData alebo updateStyle
        if "updateDispMData" in result or "updateStyle" in result or "updateDispMs" in result:
            print(f"    *** OBSAHUJE UPDATE LOGIC ***")
            # Ziskaj prve 2000 znakov
            print(f"    First 2000 chars:")
            print(result[:2000])
            print("\n" + "="*80 + "\n")

# 2. Skusam HTML stranku
print("\n[2] Skusam HTML stranku...")
html = raw_get("/")
if "js/" in html or ".js" in html:
    import re
    js_refs = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html)
    print(f"    JS odkazy: {js_refs}")
    for js in js_refs:
        if not js.startswith("http"):
            js_path = f"/esls_new/{js}" if not js.startswith("/") else js
            result = raw_get(js_path)
            if "updateDispMData" in result or "updateStyle" in result or "updateDispMs" in result:
                print(f"\n    *** {js_path} OBSAHUJE UPDATE LOGIC ***")
                print(result[:3000])
