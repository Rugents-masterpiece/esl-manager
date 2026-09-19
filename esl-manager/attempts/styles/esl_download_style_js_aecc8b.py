#!/usr/bin/env python3
"""Stiahni a analyzuje app/js/style.js."""
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

# 2. Stiahni app/js/style.js
print("\n[2] Stiahnem app/js/style.js...")
try:
    with opener.open(f"{ESL_BASE}/app/js/style.js", timeout=15) as resp:
        js = resp.read().decode("utf-8", errors="replace")
        print(f"    style.js length: {len(js)}")
        
        # Uloz si to
        with open("/tmp/esl_style.js", "w") as f:
            f.write(js)
        
        # Hladaj modifyStyle funkciu
        print("\n=== modifyStyle funkcia ===")
        idx = js.find("function modifyStyle")
        if idx >= 0:
            end = js.find("});", idx + 2000)
            if end < 0:
                end = min(len(js), idx + 2000)
            print(js[idx:end+20])
        
        # Hladaj vsetky ajax call s updateStyle
        print("\n=== VSETKY updateStyle ajax ===")
        for match in re.finditer(r'updateStyle', js):
            start = max(0, match.start() - 500)
            end = min(len(js), match.end() + 500)
            print(f"\n--- Pozicia {match.start()} ---")
            print(js[start:end])
        
        # Hladaj getDispMsData
        print("\n=== getDispMsData ===")
        for match in re.finditer(r'getDispMsData', js):
            start = max(0, match.start() - 200)
            end = min(len(js), match.end() + 500)
            print(f"\n--- Pozicia {match.start()} ---")
            print(js[start:end])
            
except Exception as e:
    print(f"    Chyba: {e}")
