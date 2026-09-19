#!/usr/bin/env python3
"""Najdi endpoint na update orderJson v HTML a JS suboroch."""
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

# 1. Skus vsetky JSP/HTML subory
print("[1] Skusam vsetky JSP/HTML subory...")
paths_to_try = [
    "/main/index",
    "/style/index.jsp",
    "/style/index.html",
    "/associate/index.jsp",
    "/associate/index.html",
    "/tag/index.jsp",
    "/tag/index.html",
    "/mms/index.jsp",
    "/mms/index.html",
    "/index.jsp",
    "/index.html",
]
for path in paths_to_try:
    try:
        with opener.open(f"{ESL_BASE}{path}", timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            if "updateDispMData" in html or "updateStyle" in html or "orderJson" in html:
                print(f"    NASHIEL v {path}!")
                # Hladaj kontext
                for keyword in ["updateDispMData", "updateStyle", "orderJson"]:
                    if keyword in html:
                        idx = html.find(keyword)
                        snippet = html[max(0,idx-200):idx+500]
                        print(f"      {keyword} kontext:\n{snippet[:500]}")
    except Exception as e:
        print(f"    {path}: {e}")

# 2. Skus vsetky JS subory
print("\n[2] Skusam vsetky JS subory...")
js_paths = [
    "/app/js/style.js",
    "/app/js/tag.js",
    "/app/js/index.js",
    "/assets/scripts/app.js",
    "/assets/plugins/jquery-1.10.2.min.js",
]
for js_path in js_paths:
    try:
        with opener.open(f"{ESL_BASE}{js_path}", timeout=10) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            if "updateDispMData" in js or "orderJson" in js:
                print(f"    NASHIEL v {js_path}!")
                for keyword in ["updateDispMData", "orderJson"]:
                    if keyword in js:
                        idx = js.find(keyword)
                        snippet = js[max(0,idx-300):idx+500]
                        print(f"      {keyword} kontext:\n{snippet[:500]}")
    except Exception as e:
        print(f"    {js_path}: {e}")

# 3. Skus najst endpointy v style.js
print("\n[3] Detailna analyza style.js...")
with opener.open(f"{ESL_BASE}/app/js/style.js", timeout=15) as resp:
    style_js = resp.read().decode("utf-8", errors="replace")

# Hladaj vsetky ajax call
print("    Vsetky ajax call v style.js:")
for m in re.finditer(r'\.ajax\(\{[^}]*url\s*:\s*["\']([^"\']+)["\'][^}]*\}', style_js):
    print(f"      {m.group(1)}")

# Hladaj vsetky ajaxSubmit call
print("\n    Vsetky ajaxSubmit call v style.js:")
for m in re.finditer(r'\.ajaxSubmit\(\{[^}]*url\s*:\s*["\']([^"\']+)["\'][^}]*\}', style_js):
    print(f"      {m.group(1)}")

# Hladaj funkcie
print("\n    Vsetky funkcie v style.js:")
for m in re.finditer(r'function\s+(\w+)\s*\(', style_js):
    print(f"      {m.group(1)}")

# 4. Skus najst endpointy v tag.js
print("\n[4] Detailna analyza tag.js...")
with opener.open(f"{ESL_BASE}/app/js/tag.js", timeout=15) as resp:
    tag_js = resp.read().decode("utf-8", errors="replace")

# Hladaj vsetky ajax call
print("    Vsetky ajax call v tag.js:")
for m in re.finditer(r'\.ajax\(\{[^}]*url\s*:\s*["\']([^"\']+)["\'][^}]*\}', tag_js):
    print(f"      {m.group(1)}")

# Hladaj vsetky ajaxSubmit call
print("\n    Vsetky ajaxSubmit call v tag.js:")
for m in re.finditer(r'\.ajaxSubmit\(\{[^}]*url\s*:\s*["\']([^"\']+)["\'][^}]*\}', tag_js):
    print(f"      {m.group(1)}")

# Hladaj funkcie
print("\n    Vsetky funkcie v tag.js:")
for m in re.finditer(r'function\s+(\w+)\s*\(', tag_js):
    print(f"      {m.group(1)}")
