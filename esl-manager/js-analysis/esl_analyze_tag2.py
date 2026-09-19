#!/usr/bin/env python3
"""Analyzuje tag.js a app.js pre endpointy."""
import re

# Analyzuje tag.js
print("=== tag.js ===")
with open("/tmp/esl_tag.js", "r") as f:
    tag_js = f.read()

print(f"Length: {len(tag_js)}")

# Hladaj updateDispMData
if "updateDispMData" in tag_js:
    print("NASHIEL updateDispMData!")
    idx = tag_js.find("updateDispMData")
    print(tag_js[max(0,idx-200):idx+500])
else:
    print("updateDispMData NENASHIEL")

# Hladaj vsetky endpointy
urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', tag_js))
print(f"\nVsetky endpointy ({len(urls)}):")
for u in sorted(urls):
    print(f"  {u}")

# Hladaj ajax call
ajax = set(re.findall(r'url\s*:\s*["\']([^"\']+)["\']', tag_js))
print(f"\nVsetky ajax call ({len(ajax)}):")
for u in sorted(ajax):
    print(f"  {u}")
