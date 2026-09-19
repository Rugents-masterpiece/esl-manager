#!/usr/bin/env python3
"""Login a stiahni main.js."""
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

# 2. Stiahni main.js
print("\n[2] Stiahnem main.js...")
try:
    with opener.open(f"{ESL_BASE}/assets/scripts/main.js", timeout=15) as resp:
        js = resp.read().decode("utf-8", errors="replace")
        print(f"    main.js length: {len(js)}")
        
        # Hladaj updateDispMData alebo updateStyle
        if "updateDispMData" in js:
            print("    NASHIEL updateDispMData!")
            idx = js.find("updateDispMData")
            print(f"    Kontext: {js[max(0,idx-200):idx+500]}")
        if "updateStyle" in js:
            print("    NASHIEL updateStyle!")
            idx = js.find("updateStyle")
            print(f"    Kontext: {js[max(0,idx-200):idx+500]}")
            
        # Hladaj vsetky URL endpointy
        urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', js))
        print(f"\n=== VSETKY URL ===")
        for u in sorted(urls):
            print(f"  {u}")
            
except Exception as e:
    print(f"    Chyba: {e}")
