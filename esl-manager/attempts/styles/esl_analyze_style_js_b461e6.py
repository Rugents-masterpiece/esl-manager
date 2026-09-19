#!/usr/bin/env python3
"""Analyzuje style.js pre updateStyle logiku."""
import re

with open("/tmp/esl_style.js", "r") as f:
    content = f.read()

# Hladaj modifyStyle funkciu
print("=== modifyStyle funkcia ===")
idx = content.find("function modifyStyle")
if idx >= 0:
    end = content.find("}", idx + 2000)
    print(content[idx:end+100])

# Hladaj vsetky ajax call s updateStyle
print("\n=== VSETKY updateStyle ajax ===")
for match in re.finditer(r'updateStyle', content):
    start = max(0, match.start() - 500)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])

# Hladaj getDispMsData
print("\n=== getDispMsData ===")
for match in re.finditer(r'getDispMsData', content):
    start = max(0, match.start() - 200)
    end = min(len(content), match.end() + 500)
    print(f"\n--- Pozicia {match.start()} ---")
    print(content[start:end])
