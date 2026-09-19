#!/usr/bin/env python3
"""Login a analyzuje vsetky JS subory."""
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

# 2. Stiahni index.html
print("\n[2] Stiahnem index.html...")
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
            
except Exception as e:
    print(f"    Chyba: {e}")

# 3. Stiahni vsetky JS subory
print("\n[3] Stiahnem vsetky JS subory...")
js_files = [
    "assets/scripts/app.js",
    "assets/scripts/login-soft.js",
    "assets/plugins/jquery-1.10.2.min.js",
    "assets/plugins/bootstrap/js/bootstrap.min.js",
]

for js_file in js_files:
    try:
        with opener.open(f"{ESL_BASE}/{js_file}", timeout=10) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            print(f"\n    {js_file}: {len(js)} chars")
            
            # Hladaj endpointy
            urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', js))
            if urls:
                print(f"      URL: {sorted(urls)}")
            
            # Hladaj updateDispMData
            if "updateDispMData" in js:
                print(f"      NASHIEL updateDispMData!")
                idx = js.find("updateDispMData")
                print(f"      Kontext: {js[max(0,idx-200):idx+500]}")
                
            # Hladaj updateStyle
            if "updateStyle" in js:
                print(f"      NASHIEL updateStyle!")
                idx = js.find("updateStyle")
                print(f"      Kontext: {js[max(0,idx-200):idx+500]}")
                
    except Exception as e:
        print(f"\n    {js_file}: Chyba - {e}")
