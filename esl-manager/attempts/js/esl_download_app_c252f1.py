#!/usr/bin/env python3
"""Stiahni a analyzuje app.js (hlavny dashboard JS)."""
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
    raw = resp.read()

# 2. Stiahni app.js
print("\n[2] Stiahnem app.js...")
with opener.open(f"{ESL_BASE}/assets/scripts/app.js", timeout=15) as resp:
    app_js = resp.read().decode("utf-8", errors="replace")

print(f"    Length: {len(app_js)}")

# Ulož si to
with open("/tmp/esl_app.js", "w") as f:
    f.write(app_js)

# 3. Analyzuje app.js
print("\n[3] Analyzuje app.js...")

# Hladaj updateDispMData
if "updateDispMData" in app_js:
    print("    NASHIEL updateDispMData!")
    idx = app_js.find("updateDispMData")
    print(f"    Kontext: {app_js[max(0,idx-300):idx+500]}")
else:
    print("    updateDispMData NENASHIEL")

# Hladaj updateStyle
if "updateStyle" in app_js:
    print("    NASHIEL updateStyle!")
    idx = app_js.find("updateStyle")
    print(f"    Kontext: {app_js[max(0,idx-300):idx+500]}")

# Hladaj vsetky endpointy
urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', app_js))
print(f"\n    Vsetky endpointy ({len(urls)}):")
for u in sorted(urls):
    print(f"      {u}")

# Hladaj ajax call
ajax = set(re.findall(r'url\s*:\s*["\']([^"\']+)["\']', app_js))
print(f"\n    Vsetky ajax call ({len(ajax)}):")
for u in sorted(ajax):
    print(f"      {u}")
