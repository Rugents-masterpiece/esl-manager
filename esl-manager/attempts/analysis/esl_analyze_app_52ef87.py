#!/usr/bin/env python3
"""Analyzuje app.js pre update logiku."""
import re

with open("/tmp/esl_app.js", "r") as f:
    content = f.read()

print(f"Total length: {len(content)}")

# Hladaj updateDispMData
print("\n=== updateDispMData ===")
for match in re.finditer(r'updateDispMData', content):
    start = max(0, match.start() - 300)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])

# Hladaj updateStyle
print("\n=== updateStyle ===")
for match in re.finditer(r'updateStyle', content):
    start = max(0, match.start() - 300)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])

# Hladaj vsetky URL endpointy
print("\n=== VSETKY URL endpointy ===")
urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', content))
for u in sorted(urls):
    print(f"  {u}")
