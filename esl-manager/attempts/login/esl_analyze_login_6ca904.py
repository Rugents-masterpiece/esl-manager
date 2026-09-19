#!/usr/bin/env python3
"""Analyzuje login stranku."""
import re, json, urllib.request

ESL_BASE = "http://192.168.16.251/esls_new"

# Ziskaj login stranku
print("[1] Ziskujem login stranku...")
req = urllib.request.Request(f"{ESL_BASE}/")
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"    HTML length: {len(html)}")
        
        # Najdi form action
        forms = re.findall(r'<form[^>]*action=["\']?([^"\'>\s]*)["\']?', html)
        print(f"\n=== FORM ACTION ===")
        for f in forms:
            print(f"  {f}")
        
        # Najdi vsechny inputy
        inputs = re.findall(r'<input[^>]*>', html)
        print(f"\n=== INPUTY ===")
        for inp in inputs:
            print(f"  {inp}")
        
        # Najdi script src
        scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
        print(f"\n=== SCRIPT SRC ===")
        for s in scripts:
            print(f"  {s}")
        
        # Najdi inline scripty s login logikou
        inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for i, script in enumerate(inline_scripts):
            if 'login' in script.lower() or 'submit' in script.lower() or 'passwd' in script.lower():
                print(f"\n--- Inline script {i} ---")
                print(script[:2000])

except urllib.error.HTTPError as e:
    print(f"    HTTP {e.code}")
