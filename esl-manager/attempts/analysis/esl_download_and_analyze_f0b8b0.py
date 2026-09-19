#!/usr/bin/env python3
"""Stiahne app.js a analyzuje ho."""
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

# Stiahni app.js
print("[1] Stiahujem app.js...")
app_js = raw_get("/assets/scripts/app.js")
print(f"    Length: {len(app_js)}")

with open("/tmp/esl_app.js", "w") as f:
    f.write(app_js)

# Hladaj updateDispMData
print("\n[2] Hladam updateDispMData...")
for match in re.finditer(r'.{300}(updateDispMData).{300}', app_js, re.DOTALL):
    print(match.group())
    print("=" * 80)

# Hladaj updateStyle
print("\n[3] Hladam updateStyle...")
for match in re.finditer(r'.{300}(updateStyle).{300}', app_js, re.DOTALL):
    print(match.group())
    print("=" * 80)

# Hladaj updateDispMs
print("\n[4] Hladam updateDispMs...")
for match in re.finditer(r'.{300}(updateDispMs).{300}', app_js, re.DOTALL):
    print(match.group())
    print("=" * 80)

# Hladaj AJAX post volania
print("\n[5] Hladam AJAX POST volania...")
ajax_matches = re.findall(r'\$\.ajax\(\{[^}]*url:[^}]*\}', app_js, re.DOTALL)
for i, match in enumerate(ajax_matches[:20]):
    print(f"\n--- AJAX {i} ---")
    print(match[:500])

# Hladaj $.post volania
print("\n[6] Hladam $.post volania...")
post_matches = re.findall(r'\$\.post\([^)]+\)', app_js)
for i, match in enumerate(post_matches[:20]):
    print(f"\n--- POST {i} ---")
    print(match[:300])
