#!/usr/bin/env python3
"""Analyzuje tag.js a app.js pre endpointy."""
import re

# Analyzuje tag.js
print("=== tag.js ===")
with open("/tmp/esl_app_js.js", "r") as f:
    content = f.read()

print(f"Length: {len(content)}")

# Hladaj updateDispMData
if "updateDispMData" in content:
    print("NASHIEL updateDispMData!")
    idx = content.find("updateDispMData")
    print(content[max(0,idx-200):idx+500])
else:
    print("updateDispMData NENASHIEL")

# Hladaj vsetky endpointy
urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', content))
print(f"\nVsetky endpointy ({len(urls)}):")
for u in sorted(urls):
    print(f"  {u}")

# Hladaj ajax call
ajax = set(re.findall(r'url\s*:\s*["\']([^"\']+)["\']', content))
print(f"\nVsetky ajax call ({len(ajax)}):")
for u in sorted(ajax):
    print(f"  {u}")
