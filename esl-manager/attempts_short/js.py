#!/usr/bin/env python3
"""
ESL Manager - Konsolidovaný JS download a analýza skript
Zhrnutie 10 pôvodných skriptov z attempts/js/

Cieľ: Stiahnuť a analyzovať JavaScriptové súbory z ESL dashboardu.

Súbory na stiahnutie:
  - /app/js/app.js (Bootstrap framework, 42KB)
  - /app/js/style.js (správa štýlov)
  - /app/js/tag.js (správa tagov)
  - /app/js/index.js (nastavenia jazyka)

Výsledky:
  - app.js je len Bootstrap - žiadna ESL logika
  - style.js obsahuje modifyStyle, updateStyle logiku
  - tag.js obsahuje tag/update, tag/addTag, ajaxSubmit logiku
  - index.js je len pre i18n
  - updateDispMData NIE JE v žiadnom JS súbore!
  - orderJson NIE JE v žiadnom JS súbore!

Kľúčové zistenia z tag.js:
  1. ajaxSubmit používa $('#modifyTagForm').serialize() - form-encoded data
  2. contentType je 'application/json' ale data sú form-encoded
  3. tag/update endpoint existuje
  4. tag/updateTag endpoint existuje
  5. tag/addTag endpoint existuje
  6. getStylesData endpoint existuje
"""

import json
import urllib.request
import re


def download_js(base_url, path, title=""):
    """Stiahni JS súbor a analyzuj ho."""
    url = f"{base_url}{path}"
    print(f"\n[DOWNLOAD] {title}: {url}")

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            print(f"  Dĺžka: {len(js)}")

            # Ulož do /tmp
            filename = path.split('/')[-1] if '/' in path else path
            with open(f"/tmp/esl_{filename}", "w") as f:
                f.write(js)
            print(f"  Uložené: /tmp/esl_{filename}")

            # Analyzuj
            analyze_js_content(js, title)

    except Exception as e:
        print(f"  Chyba: {e}")


def analyze_js_content(js, title=""):
    """Analyzuj obsah JS súboru."""
    print(f"\n  [ANALYSIS] {title}")

    # Nájdi endpointy
    endpoints = re.findall(r'["\'](/[^"\']*[^"\'])["\']', js)
    api_endpoints = [e for e in endpoints if any(kw in e.lower() for kw in ['style', 'tag', 'login', 'disp', 'update', 'get', 'add', 'delete'])]
    if api_endpoints:
        print(f"  API endpointy ({len(set(api_endpoints))}):")
        for ep in sorted(set(api_endpoints)):
            print(f"    {ep}")

    # Nájdi funkcie
    functions = re.findall(r'function\s+(\w+)', js)
    if functions:
        print(f"  Funkcie ({len(set(functions))}):")
        for func in sorted(set(functions))[:20]:
            print(f"    {func}")

    # Hľadaj kľúčové termíny
    terms = ['updateDispMData', 'orderJson', 'updateStyle', 'modifyStyle', 'addStyle',
             'ajaxSubmit', 'serialize', 'contentType', 'application/json']
    for term in terms:
        count = js.count(term)
        if count > 0:
            print(f"  '{term}': {count} výskytov")

    # Nájdi ajaxSubmit volania
    ajax_calls = re.findall(r'ajaxSubmit\([^)]+\)', js)
    if ajax_calls:
        print(f"\n  ajaxSubmit volania ({len(ajax_calls)}):")
        for call in ajax_calls[:3]:
            print(f"    {call[:200]}")

    # Nájdi contentType
    content_types = re.findall(r'contentType:\s*["\']([^"\']+)["\']', js)
    if content_types:
        print(f"\n  contentType: {set(content_types)}")


def find_js_in_html(base_url, html_url, title=""):
    """Nájdi JS reference v HTML."""
    print(f"\n[HTML_JS] {title}: {html_url}")
    try:
        with urllib.request.urlopen(html_url, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            print(f"  Dĺžka HTML: {len(html)}")

            # Nájdi script src
            scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
            if scripts:
                print(f"  Script src ({len(scripts)}):")
                for s in scripts:
                    print(f"    {s}")

            # Nájdi inline scripty
            inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
            for i, script in enumerate(inline_scripts):
                if len(script.strip()) > 50:
                    print(f"  Inline script {i}: {script[:200]}...")

    except Exception as e:
        print(f"  Chyba: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("ESL Manager - Konsolidovaný JS download skript")
    print("=" * 60)

    ESL_BASE = "http://192.168.16.251/esls_new"

    # 1. Stiahni a analyzuj všetky JS súbory
    js_files = [
        ("/app/js/app.js", "app.js - Bootstrap"),
        ("/app/js/style.js", "style.js - Štýly"),
        ("/app/js/tag.js", "tag.js - Tagy"),
        ("/app/js/index.js", "index.js - Jazyk"),
    ]

    for path, title in js_files:
        download_js(ESL_BASE, path, title)

    # 2. Nájdi JS reference v HTML
    print("\n" + "=" * 60)
    print("=== HTML JS REFERENCE ===")
    find_js_in_html(ESL_BASE, f"{ESL_BASE}/", "Login stránka")
    find_js_in_html(ESL_BASE, f"{ESL_BASE}/main/index", "Main dashboard")

    print("\n[RESULT] Kľúčové zistenia:")
    print("  1. app.js je len Bootstrap - žiadna ESL logika")
    print("  2. style.js obsahuje modifyStyle, updateStyle logiku")
    print("  3. tag.js obsahuje tag/update, tag/addTag, ajaxSubmit logiku")
    print("  4. index.js je len pre i18n - nepodstatný")
    print("  5. updateDispMData NIE JE v žiadnom JS súbore!")
    print("  6. orderJson NIE JE v žiadnom JS súbore!")
    print("  7. ajaxSubmit používa serialize() - form-encoded data")
    print("  8. contentType je 'application/json' ale data sú form-encoded")

    print("\n[OK] JS download skript dokončený.")
