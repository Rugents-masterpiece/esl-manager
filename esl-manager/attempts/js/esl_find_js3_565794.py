#!/usr/bin/env python3
"""Stiahne HTML a najde vsetky odkazy na JSP/HTML subory."""
import re, urllib.request

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def raw_get(path):
    url = f"{ESL_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except:
        return None

html = raw_get("/")
print(f"HTML length: {len(html)}")

# Najdi vsechny odkazy
print("\n=== VSETKY ODKAZY ===")
links = re.findall(r'href=["\']([^"\']+)["\']', html)
for link in links:
    print(f"  {link}")

# Najdi vsechny script src
print("\n=== VSETKY SCRIPT SRC ===")
scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\'][^>]*>', html)
for s in scripts:
    print(f"  {s}")

# Najdi inline scripty
print("\n=== INLINE SCRIPTS ===")
inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for i, script in enumerate(inline_scripts):
    if len(script.strip()) > 50:
        print(f"\n--- Inline script {i} ({len(script)} chars) ---")
        print(script[:3000])
