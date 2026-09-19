#!/usr/bin/env python3
"""Analyzuje tag.js pre updateDispMData."""
import re

with open("/tmp/esl_tag.js", "r") as f:
    content = f.read()

print(f"Total length: {len(content)}")

# Hladaj updateDispMData
print("\n=== updateDispMData ===")
for match in re.finditer(r'updateDispMData', content):
    start = max(0, match.start() - 300)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])

# Hladaj updateStyleMsg
print("\n=== updateStyleMsg ===")
for match in re.finditer(r'updateStyleMsg', content):
    start = max(0, match.start() - 300)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])
