#!/usr/bin/env python3
"""Analyzuje app/js/index.js a hladaj updateDispMData."""
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

# Stiahni app/js/index.js
with opener.open(f"{ESL_BASE}/app/js/index.js", timeout=15) as resp:
    js = resp.read().decode("utf-8", errors="replace")

print(f"Total length: {len(js)}")

# Hladaj vsetky endpointy
print("\n=== VSETKY ENDPOINTY V index.js ===")
for m in re.finditer(r'["\'](/[^"\']*(?:update|style|disp|tag|json)[^"\']*)["\']', js, re.IGNORECASE):
    print(f"  {m.group(1)}")

# Hladaj vsetky ajax call
print("\n=== VSETKY AJAX CALL V index.js ===")
for m in re.finditer(r'\.ajax\(\{[^}]*url\s*:\s*["\']([^"\']+)["\'][^}]*\}', js):
    print(f"  {m.group(1)}")

# Hladaj vsetky funkcie
print("\n=== VSETKY FUNKCIE V index.js ===")
for m in re.finditer(r'function\s+(\w+)\s*\(', js):
    print(f"  {m.group(1)}")

# Hladaj inline JavaScript v HTML
print("\n=== INLINE JAVASCRIPT V main/index ===")
with opener.open(f"{ESL_BASE}/main/index", timeout=15) as resp:
    html = resp.read().decode("utf-8", errors="replace")

for m in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
    script = m.group(1)
    if len(script.strip()) > 10:
        print(f"\n  Inline script ({len(script)} chars):")
        print(f"    {script[:2000]}")

# Hladaj dynamicke importy
print("\n=== DYNAMICKE IMPORTY ===")
for m in re.finditer(r'(import|require|loadModule|loadScript)\s*\([^)]*\)', js):
    print(f"  {m.group(0)}")

# Hladaj vsetky URL v index.js
print("\n=== VSETKY URL V index.js ===")
urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', js))
for u in sorted(urls):
    print(f"  {u}")
