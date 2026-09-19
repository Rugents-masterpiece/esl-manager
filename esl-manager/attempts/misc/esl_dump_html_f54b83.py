#!/usr/bin/env python3
"""Dump main/index a hladaj vsetky endpointy."""
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

# Hladaj vsetky slova obsahujuce "update", "order", "DispM", "field", "style"
print("\n=== VSETKY VÝSKYTY KLÚČOVÝCH SLOV ===")
keywords = ["update", "order", "DispM", "field", "style", "json", "ajax", "submit"]
for kw in keywords:
    count = html.lower().count(kw.lower())
    if count > 0:
        print(f"  {kw}: {count} výskytov")

# Hladaj inline JavaScript
print("\n=== INLINE JAVASCRIPT ===")
for m in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
    script = m.group(1)
    if len(script.strip()) > 50:
        print(f"\n  Inline script ({len(script)} chars):")
        # Hladaj klucove slova
        for kw in ["update", "order", "DispM", "field", "ajax", "submit"]:
            if kw.lower() in script.lower():
                idx = script.lower().find(kw.lower())
                snippet = script[max(0,idx-100):idx+300]
                print(f"    {kw}: {snippet[:400]}")

# Hladaj vsetky URL endpointy v HTML
print("\n=== VSETKY URL ENDPOINTY V HTML ===")
urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', html))
for u in sorted(urls):
    print(f"  {u}")

# Hladaj vsetky URL endpointy v HTML (bez /esls_new/)
print("\n=== VSETKY URL ENDPOINTY V HTML (bez /esls_new/) ===")
urls2 = set(re.findall(r'["\'](/[^"\']+(?:update|order|DispM|field|style)[^"\']*)["\']', html, re.IGNORECASE))
for u in sorted(urls2):
    print(f"  {u}")

# Hladaj vsetky URL endpointy v HTML (vsetky)
print("\n=== VSETKY URL V HTML ===")
urls3 = set(re.findall(r'["\'](/[^"\']+)["\']', html))
for u in sorted(urls3):
    if not u.startswith('/assets/') and not u.startswith('/app/') and not u.startswith('/favicon') and not u.startswith('/img/'):
        print(f"  {u}")
