#!/usr/bin/env python3
"""Analyzuje HTML stranku ESL dashboardu."""
import re, json, urllib.request

ESL_BASE = "http://192.168.16.251/esls_new"
SESSION_ID = "06DAE8066D63A0CC3DCDEB1D8E360F4B"

def raw_get(path):
    url = f"{ESL_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Cookie", f"JSESSIONID={SESSION_ID}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"ERROR: {e}"

html = raw_get("/")
print(f"HTML length: {len(html)}")

# Najdi vsetky script src
print("\n=== SCRIPT SRC ===")
scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\'][^>]*>', html)
for s in scripts:
    print(f"  {s}")

# Najdi inline scripty
print("\n=== INLINE SCRIPTS ===")
inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for i, script in enumerate(inline_scripts):
    if len(script.strip()) > 50:
        print(f"\n--- Inline script {i} ({len(script)} chars) ---")
        print(script[:2000])

# Hladaj aj odkazy na JSP/HTML subory
print("\n=== ODKAZY V HTML ===")
links = re.findall(r'href=["\']([^"\']+)["\']', html)
for link in links:
    if '.jsp' in link or '.html' in link or 'style' in link.lower() or 'update' in link.lower():
        print(f"  {link}")

# Hladaj aj form action
print("\n=== FORM ACTION ===")
forms = re.findall(r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>', html)
for f in forms:
    print(f"  {f}")

# Hladaj aj AJAX URL patterns
print("\n=== AJAX URL PATTERNS ===")
ajax_patterns = re.findall(r'(?:url|ajax)\s*[:=]\s*["\']([^"\']*)["\']', html, re.IGNORECASE)
for m in ajax_patterns:
    print(f"  {m}")
