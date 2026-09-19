#!/usr/bin/env python3
"""Analyzuje main/index.html podrobne."""
import re, urllib.request, http.cookiejar, hashlib, urllib.parse

ESL_BASE = "http://192.168.16.251/esls_new"

# Login
passwd_md5 = hashlib.md5(b"admin").hexdigest()
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
login_data = {"username": "admin", "passwd": passwd_md5}
body = urllib.parse.urlencode(login_data, encoding="utf-8").encode("utf-8")
req = urllib.request.Request(f"{ESL_BASE}/login/userLogin", data=body, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
req.add_header("X-Requested-With", "XMLHttpRequest")
with opener.open(req, timeout=15) as resp:
    resp.read()

# Stiahni main/index
with opener.open(f"{ESL_BASE}/main/index", timeout=15) as resp:
    html = resp.read().decode("utf-8", errors="replace")

print(f"Total length: {len(html)}")

# Hladaj vsetky script tagy
print("\n=== SCRIPT TAGY ===")
for m in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
    script = m.group(1)
    if len(script.strip()) > 10:
        if "updateDispMData" in script:
            print(f"\n    NASHIEL updateDispMData v inline script!")
            idx = script.find("updateDispMData")
            print(f"    Kontext:\n{script[max(0,idx-500):idx+1500]}")
        if "updateStyle" in script:
            print(f"\n    NASHIEL updateStyle v inline script!")
            idx = script.find("updateStyle")
            print(f"    Kontext:\n{script[max(0,idx-500):idx+1500]}")

# Hladaj vsetky src atributy
print("\n=== SRC ATRIBUTY ===")
for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\']', html):
    print(f"  {m.group(1)}")

# Hladaj vsetky inline JS s updateDispMData
print("\n=== INLINE JS S updateDispMData ===")
for m in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
    script = m.group(1)
    if "updateDispMData" in script:
        print(f"    NASHIEL!")
        idx = script.find("updateDispMData")
        print(f"    {script[max(0,idx-300):idx+1000]}")

# Hladaj vsetky JS soubory
print("\n=== VSETKY JS SUBORY ===")
js_files = set()
for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\']', html):
    js_files.add(m.group(1))
for f in sorted(js_files):
    print(f"  {f}")

# Stiahni vsetky JS subory a hladaj updateDispMData
print("\n=== ANALYZUJEM VSETKY JS SUBORY ===")
for js_path in sorted(js_files):
    full_url = f"{ESL_BASE}{js_path}" if js_path.startswith("/") else f"{ESL_BASE}/{js_path}"
    try:
        with opener.open(full_url, timeout=10) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            if "updateDispMData" in js:
                print(f"\n    NASHIEL updateDispMData v: {js_path}")
                idx = js.find("updateDispMData")
                snippet = js[max(0,idx-500):idx+1500]
                print(f"    Kontext:\n{snippet}")
    except Exception as e:
        print(f"    Chyba {js_path}: {e}")
