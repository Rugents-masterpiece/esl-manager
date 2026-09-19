#!/usr/bin/env python3
"""Najdi updateDispMData vo vsetkych JS suboroch."""
import json, urllib.request, urllib.parse, hashlib, re, http.cookiejar, os

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
    raw = resp.read()

# 2. Stiahni vsetky JS subory
print("\n[2] Stiahnem vsetky JS subory...")
js_files = [
    "app/js/style.js",
    "app/js/tag.js",
    "app/js/main.js",
    "app/js/index.js",
    "assets/scripts/app.js",
    "assets/scripts/login-soft.js",
]

for js_path in js_files:
    try:
        with opener.open(f"{ESL_BASE}/{js_path}", timeout=10) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            filename = js_path.replace("/", "_").replace(".", "_") + ".js"
            with open(f"/tmp/esl_{filename}", "w") as f:
                f.write(js)
            
            # Hladaj updateDispMData
            if "updateDispMData" in js:
                print(f"\n    NASHIEL updateDispMData v: {js_path}")
                idx = js.find("updateDispMData")
                print(f"    Kontext: {js[max(0,idx-300):idx+500]}")
    except Exception as e:
        print(f"    Chyba: {js_path} - {e}")

# 3. Hladaj vsetky endpointy vo vsetkych JS suboroch
print("\n[3] Vsetky endpointy vo vsetkych JS suboroch...")
all_urls = set()
for js_path in js_files:
    try:
        with opener.open(f"{ESL_BASE}/{js_path}", timeout=10) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', js))
            all_urls.update(urls)
    except:
        pass

for u in sorted(all_urls):
    print(f"  {u}")

# 4. Hladaj vsetky ajax call
print("\n[4] Vsetky ajax call vo vsetkych JS suboroch...")
all_ajax = set()
for js_path in js_files:
    try:
        with opener.open(f"{ESL_BASE}/{js_path}", timeout=10) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            ajax = set(re.findall(r'url\s*:\s*["\']([^"\']+)["\']', js))
            all_ajax.update(ajax)
    except:
        pass

for u in sorted(all_ajax):
    print(f"  {u}")
