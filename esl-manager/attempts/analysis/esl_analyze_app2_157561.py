#!/usr/bin/env python3
"""Analyzuje app.js pre update logiku."""
import re

with open("/tmp/esl_app.js", "r") as f:
    content = f.read()

print(f"Total length: {len(content)}")

# Hladaj vsechny URL endpointy
print("\n=== VSETKY URL endpointy ===")
urls = re.findall(r'["\'](/esls[^"\']*)["\']', content)
for u in sorted(set(urls)):
    print(f"  {u}")

# Hladaj ajax/post/get volania
print("\n=== AJAX VOLANIA ===")
ajax_calls = re.findall(r'\$(?:ajax|post|get)\([^)]+\)', content, re.DOTALL)
for i, call in enumerate(ajax_calls[:30]):
    print(f"\n--- AJAX {i} ---")
    print(call[:500])

# Hladaj orderJson
print("\n=== orderJson reference ===")
order_matches = re.findall(r'.{100}orderJson.{100}', content, re.DOTALL)
for i, m in enumerate(order_matches[:10]):
    print(f"\n--- {i} ---")
    print(m[:300])

# Hladaj update
print("\n=== update reference ===")
update_matches = re.findall(r'.{100}update.{100}', content, re.DOTALL)
for i, m in enumerate(update_matches[:20]):
    print(f"\n--- {i} ---")
    print(m[:300])
