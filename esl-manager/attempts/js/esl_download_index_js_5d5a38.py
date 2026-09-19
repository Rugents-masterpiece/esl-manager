#!/usr/bin/env python3
"""Stiahni a analyzuje app/js/index.js."""
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

# 2. Stiahni app/js/index.js
print("\n[2] Stiahnem app/js/index.js...")
try:
    with opener.open(f"{ESL_BASE}/app/js/index.js", timeout=15) as resp:
        js = resp.read().decode("utf-8", errors="replace")
        print(f"    index.js length: {len(js)}")
        
        # Uloz si to
        with open("/tmp/esl_index.js", "w") as f:
            f.write(js)
        
        # Hladaj updateDispMData
        print("\n=== updateDispMData ===")
        for match in re.finditer(r'updateDispMData', js):
            start = max(0, match.start() - 300)
            end = min(len(js), match.end() + 500)
            print(f"\n--- Pozicia {match.start()} ---")
            print(js[start:end])
        
        # Hladaj updateStyle
        print("\n=== updateStyle ===")
        for match in re.finditer(r'updateStyle', js):
            start = max(0, match.start() - 300)
            end = min(len(js), match.end() + 500)
            print(f"\n--- Pozicia {match.start()} ---")
            print(js[start:end])
        
        # Hladaj vsetky URL endpointy
        print("\n=== VSETKY URL endpointy ===")
        urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', js))
        for u in sorted(urls):
            print(f"  {u}")
            
except Exception as e:
    print(f"    Chyba: {e}")
