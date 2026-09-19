#!/usr/bin/env python3
"""Prihlas sa do ESL dashboardu."""
import json, urllib.request, urllib.parse, hashlib

ESL_BASE = "http://192.168.16.251/esls_new"

# Skusam login
print("[1] Skusam login...")
data = {"username": "admin", "passwd": "admin"}
body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
req = urllib.request.Request(f"{ESL_BASE}/login", data=body, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
req.add_header("X-Requested-With", "XMLHttpRequest")
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"    Status: {resp.status}")
        print(f"    Headers: {dict(resp.headers)}")
        raw = resp.read()
        print(f"    Response: {repr(raw[:500])}")
except urllib.error.HTTPError as e:
    print(f"    HTTP {e.code}")
    raw = e.read()
    print(f"    Response: {repr(raw[:500])}")

# Skusam aj s MD5 heslom
print("\n[2] Skusam login s MD5...")
passwd_md5 = hashlib.md5(b"admin").hexdigest()
data2 = {"username": "admin", "passwd": passwd_md5}
body2 = urllib.parse.urlencode(data2, encoding="utf-8").encode("utf-8")
req2 = urllib.request.Request(f"{ESL_BASE}/login", data=body2, method="POST")
req2.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
req2.add_header("X-Requested-With", "XMLHttpRequest")
try:
    with urllib.request.urlopen(req2, timeout=15) as resp:
        print(f"    Status: {resp.status}")
        print(f"    Set-Cookie: {resp.headers.get('Set-Cookie')}")
        raw = resp.read()
        print(f"    Response: {repr(raw[:500])}")
except urllib.error.HTTPError as e:
    print(f"    HTTP {e.code}")
    raw = e.read()
    print(f"    Response: {repr(raw[:500])}")
