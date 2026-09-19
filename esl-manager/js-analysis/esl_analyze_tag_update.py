#!/usr/bin/env python3
"""Analyzuje tag.js pre tag/update endpoint."""
import re

with open("/tmp/esl_tag.js", "r") as f:
    content = f.read()

# Hladaj tag/update
print("=== tag/update ===")
for match in re.finditer(r'tag/update', content):
    start = max(0, match.start() - 300)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])

# Hladaj tag/updateTag
print("\n=== tag/updateTag ===")
for match in re.finditer(r'tag/updateTag', content):
    start = max(0, match.start() - 300)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])
