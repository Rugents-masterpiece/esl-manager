#!/usr/bin/env python3
"""Analyzuje index/index.html - hlavna stranka."""
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

# Stiahni index/index.html
with opener.open(f"{ESL_BASE}/index/index.html", timeout=15) as resp:
    html = resp.read().decode("utf-8", errors="replace")

print(f"Total length: {len(html)}")

# Hladaj inline JavaScript
print("\n=== INLINE JAVASCRIPT ===")
for m in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
    script = m.group(1)
    if len(script.strip()) > 50:
        print(f"\n  Inline script ({len(script)} chars):")
        print(f"    {script[:500]}")

# Hladaj vsetky URL endpointy v HTML
print("\n=== VSETKY URL V HTML ===")
urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', html))
for u in sorted(urls):
    print(f"  {u}")

# Hladaj vsetky src atributy
print("\n=== SRC ATRIBUTY ===")
for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\']', html):
    print(f"  {m.group(1)}")

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
            print(f"\n  {js_path} ({len(js)} chars)")
            if "updateDispMData" in js:
                print(f"    *** NASHIEL updateDispMData! ***")
                idx = js.find("updateDispMData")
                snippet = js[max(0,idx-500):idx+1500]
                print(f"    Kontext:\n{snippet}")
            if "updateStyle" in js:
                print(f"    NASHIEL updateStyle")
                idx = js.find("updateStyle")
                snippet = js[max(0,idx-300):idx+500]
                print(f"    Kontext:\n{snippet[:500]}")
            if "orderJson" in js:
                print(f"    NASHIEL orderJson")
                idx = js.find("orderJson")
                snippet = js[max(0,idx-300):idx+500]
                print(f"    Kontext:\n{snippet[:500]}")
    except Exception as e:
        print(f"    Chyba {js_path}: {e}")
