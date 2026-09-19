#!/usr/bin/env python3
"""Analyzuje tag.js pre vsetky endpointy."""
import re

with open("/tmp/esl_tag.js", "r") as f:
    content = f.read()

print(f"Total length: {len(content)}")

# Hladaj vsetky URL endpointy
print("\n=== VSETKY URL endpointy ===")
urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', content))
for u in sorted(urls):
    print(f"  {u}")

# Hladaj vsetky ajax call
print("\n=== VSETKY ajax call ===")
ajax_calls = re.findall(r'url\s*:\s*["\']([^"\']+)["\']', content)
for u in sorted(set(ajax_calls)):
    print(f"  {u}")
