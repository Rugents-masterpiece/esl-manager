#!/usr/bin/env python3
"""Stiahne a analyzuje JS subory z ESL dashboardu."""
import json, urllib.request, urllib.parse, re

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

# 1. Stiahni HTML stranku a najdi JS odkazy
print("[1] Stiahujem HTML stranku...")
html = raw_get("/")
print(f"    Length: {len(html)}")

# Hladaj JS odkazy
js_refs = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html)
print(f"    JS odkazy: {js_refs}")

# 2. Hladaj aj inline scripty s AJAX volanimi
print("\n[2] Hladam AJAX volania v HTML...")
ajax_refs = re.findall(r'(ajax|post|get|fetch|$.post|$.ajax|XMLHttpRequest|$.getJSON)', html)
print(f"    AJAX odkazy: {len(ajax_refs)}")

# 3. Hladaj updateDispMData alebo updateStyle v inline scriptoch
print("\n[3] Hladam updateDispMData/updateStyle v inline scriptoch...")
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for i, script in enumerate(scripts):
    if 'updateDispMData' in script or 'updateStyle' in script or 'updateDispMs' in script:
        print(f"    *** NASHLED script {i} ***")
        print(script[:2000])
        print()

# 4. Stiahni app.js
print("\n[4] Stiahujem app.js...")
app_js = raw_get("/assets/scripts/app.js")
print(f"    Length: {len(app_js)}")
if 'updateDispMData' in app_js or 'updateStyle' in app_js:
    print("    *** OBSAHUJE UPDATE LOGIC ***")
    # Najdi kontekst okolo updateDispMData
    for match in re.finditer(r'.{200}(updateDispMData|updateStyle|updateDispMs).{200}', app_js, re.DOTALL):
        print(f"    Kontext: {match.group()}")
        print()

# 5. Skusam najst JS subory v inych adresaroch
print("\n[5] Hladam JS subory v inych adresaroch...")
paths_to_try = [
    "/assets/scripts/dashboard.js",
    "/assets/scripts/esl.js",
    "/assets/scripts/style.js",
    "/assets/scripts/controller.js",
    "/assets/scripts/service.js",
    "/assets/scripts/main.js",
    "/assets/scripts/app.js",
    "/assets/scripts/login-soft.js",
]

for path in paths_to_try:
    result = raw_get(path)
    if not result.startswith("ERROR") and len(result) > 100:
        print(f"    FOUND: {path} ({len(result)} chars)")
        if 'updateDispMData' in result or 'updateStyle' in result or 'updateDispMs' in result:
            print(f"    *** OBSAHUJE UPDATE LOGIC ***")
            for match in re.finditer(r'.{200}(updateDispMData|updateStyle|updateDispMs).{200}', result, re.DOTALL):
                print(f"    Kontext: {match.group()}")
                print()

# 6. Skusam najst JS subory v /esls_new/ adresari
print("\n[6] Hladam JS subory v /esls_new/...")
html2 = raw_get("/esls_new/")
if html2 and len(html2) > 100:
    js_refs2 = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html2)
    print(f"    JS odkazy: {js_refs2}")
