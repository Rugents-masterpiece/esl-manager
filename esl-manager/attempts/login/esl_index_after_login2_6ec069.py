#!/usr/bin/env python3
"""Login a analyzuje index.html po prihlaseni."""
import json, urllib.request, urllib.parse, hashlib, re, http.cookiejar

ESL_BASE = "http://192.168.16.251/esls_new"

# 1. Login
print("[1] Login...")
passwd_md5 = hashlib.md5(b"admin").hexdigest()
data = {"username": "admin", "passwd": passwd_md5}
body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
req = urllib.request.Request(f"{ESL_BASE}/login/userLogin", data=body, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
req.add_header("X-Requested-With", "XMLHttpRequest")

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

with opener.open(req, timeout=15) as resp:
    print(f"    Status: {resp.status}")
    raw = resp.read()

# 2. Stiahni index.html po prihlaseni
print("\n[2] Stiahnem index.html po prihlaseni...")
try:
    with opener.open(f"{ESL_BASE}/index.html", timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"    HTML length: {len(html)}")
        
        # Najdi vsechny script src
        scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
        print(f"\n=== SCRIPT SRC ({len(scripts)}) ===")
        for s in scripts:
            print(f"  {s}")
        
        # Najdi vsechny URL endpointy
        urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', html))
        print(f"\n=== URL V HTML ({len(urls)}) ===")
        for u in sorted(urls):
            print(f"  {u}")
            
        # Najdi inline scripty
        inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"\n=== INLINE SCRIPTS ({len(inline_scripts)}) ===")
        for i, script in enumerate(inline_scripts):
            if len(script.strip()) > 20:
                print(f"\n--- Inline script {i} ({len(script)} chars) ---")
                print(script[:2000])
            
except Exception as e:
    print(f"    Chyba: {e}")
