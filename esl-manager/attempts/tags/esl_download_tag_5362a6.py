#!/usr/bin/env python3
"""Stiahni a analyzuje tag.js priamo z URL."""
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

# 2. Stiahni tag.js
print("\n[2] Stiahnem tag.js...")
with opener.open(f"{ESL_BASE}/app/js/tag.js", timeout=15) as resp:
    tag_js = resp.read().decode("utf-8", errors="replace")

print(f"    Length: {len(tag_js)}")

# Ulož si to
with open("/tmp/esl_tag.js", "w") as f:
    f.write(tag_js)

# 3. Analyzuje tag.js
print("\n[3] Analyzuje tag.js...")

# Hladaj tag/update
print("\n=== tag/update ===")
for match in re.finditer(r'tag/update', tag_js):
    start = max(0, match.start() - 300)
    end = min(len(tag_js), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(tag_js[start:end])

# Hladaj tag/updateTag
print("\n=== tag/updateTag ===")
for match in re.finditer(r'tag/updateTag', tag_js):
    start = max(0, match.start() - 300)
    end = min(len(tag_js), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(tag_js[start:end])

# Hladaj tag/addTag
print("\n=== tag/addTag ===")
for match in re.finditer(r'tag/addTag', tag_js):
    start = max(0, match.start() - 300)
    end = min(len(tag_js), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(tag_js[start:end])
