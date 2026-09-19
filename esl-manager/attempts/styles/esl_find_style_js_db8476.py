#!/usr/bin/env python3
"""Najdi vsetky JS subory v app/js/."""
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

# 2. Stiahni app/js/style.js (pravdepodobne pre style management)
js_files = [
    "app/js/style.js",
    "app/js/tag.js",
    "app/js/main.js",
    "app/js/esl.js",
    "app/js/esls.js",
    "app/js/styleManage.js",
    "app/js/style_manage.js",
]

for js_file in js_files:
    try:
        with opener.open(f"{ESL_BASE}/{js_file}", timeout=10) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            print(f"\n=== {js_file}: {len(js)} chars ===")
            
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
            
            # Hladaj style endpointy
            urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', js))
            style_urls = [u for u in urls if "style" in u.lower()]
            if style_urls:
                print(f"      Style URL: {style_urls}")
                
    except Exception as e:
        print(f"\n=== {js_file}: Chyba - {e}")
