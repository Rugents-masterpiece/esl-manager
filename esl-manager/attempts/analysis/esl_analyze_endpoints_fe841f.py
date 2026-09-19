#!/usr/bin/env python3
"""Analyzuje tag/update endpoint."""
import re

with open("/tmp/esl_app_js.js", "r") as f:
    content = f.read()

# Hladaj tag/update
print("=== tag/update ===")
for match in re.finditer(r'tag/update', content):
    start = max(0, match.start() - 300)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])

# Hladaj style/styleId
print("\n=== style/styleId ===")
for match in re.finditer(r'style/styleId', content):
    start = max(0, match.start() - 300)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])
