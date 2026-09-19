#!/usr/bin/env python3
"""Analyzuje HTML stranku ESL dashboardu."""
import re, json, urllib.request

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

# Najdi inline scripty
inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for i, script in enumerate(inline_scripts):
    if len(script.strip()) > 50:
        print(f"\n--- Inline script {i} ({len(script)} chars) ---")
        print(script[:3000])
