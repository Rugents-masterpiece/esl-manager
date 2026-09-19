#!/usr/bin/env python3
"""
ESL Manager - Konsolidovaný analysis skript
Zhrnutie 9 pôvodných skriptov z attempts/analysis/

Cieľ: Analýza HTML a JS súborov z ESL dashboardu.

Súbory analyzované:
  - / (login stránka)
  - /main/index (main dashboard)
  - /app/js/app.js (Bootstrap framework)
  - /app/js/style.js (správa štýlov)
  - /app/js/tag.js (správa tagov)
  - /app/js/index.js (nastavenia jazyka)

Výsledky analýzy:
  - app.js je len Bootstrap framework - žiadna ESL logika
  - style.js obsahuje logiku pre správu štýlov (modifyStyle, updateStyle)
  - tag.js obsahuje logiku pre správu tagov (tag/update, tag/addTag)
  - index.js je len pre nastavenia jazyka
  - updateDispMData NIE JE v žiadnom statickom JS súbore!
  - orderJson NIE JE v žiadnom statickom JS súbore!
  - Inline skripty v HTML neobsahujú API logiku

Kľúčové zistenia:
  1. updateDispMData endpoint nie je definovaný v žiadnom statickom súbore
  2. Je dynamicky generovaný serverom alebo v inline skripte ktorý sa nenačíta
  3. style.js a tag.js sú jediný relevantné JS súbory
  4. app.js je len Bootstrap - nepodstatný
  5. index.js je len pre i18n - nepodstatný
  6. API endpointy sú relatívne voči /esls_new/
"""

import json
import urllib.request
import re


def analyze_html(url, title=""):
    """Analýza HTML stránky."""
    print(f"\n[HTML_ANALYSIS] {title}: {url}")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            print(f"  Dĺžka: {len(html)}")

            # Nájdi form action
            forms = re.findall(r'<form[^>]*action=["\']?([^"\'>\s]*)["\']?', html)
            if forms:
                print(f"  Formy: {forms}")

            # Nájdi script src
            scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
            if scripts:
                print(f"  Scripty: {scripts}")

            # Nájdi inline scripty s login/API logikou
            inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
            for i, script in enumerate(inline_scripts):
                if any(kw in script.lower() for kw in ['login', 'submit', 'passwd', 'ajax', 'update', 'style', 'tag']):
                    print(f"  Inline script {i}: {script[:200]}...")

    except Exception as e:
        print(f"  Chyba: {e}")


def analyze_js(url, title="", search_terms=None):
    """Analýza JavaScriptového súboru."""
    print(f"\n[JS_ANALYSIS] {title}: {url}")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            print(f"  Dĺžka: {len(js)}")

            # Nájdi endpointy
            endpoints = re.findall(r'["\'](/[^"\']*[^"\'])["\']', js)
            api_endpoints = [e for e in endpoints if any(kw in e.lower() for kw in ['style', 'tag', 'login', 'disp', 'update', 'get'])]
            if api_endpoints:
                print(f"  API endpointy: {set(api_endpoints)}")

            # Hľadaj search terms
            if search_terms:
                for term in search_terms:
                    count = js.count(term)
                    if count > 0:
                        print(f"  '{term}': {count} výskytov")
                        # Nájdi kontext
                        for match in re.finditer(term, js):
                            start = max(0, match.start() - 100)
                            end = min(len(js), match.end() + 100)
                            print(f"    Kontext: ...{js[start:end]}...")
                            break  # Len prvý výskyt

    except Exception as e:
        print(f"  Chyba: {e}")


def analyze_all_js(base_url):
    """Analýza všetkých JS súborov."""
    search_terms = ['updateDispMData', 'orderJson', 'updateStyle', 'modifyStyle', 'addStyle', 'ajaxSubmit']

    js_files = [
        (f"{base_url}/app/js/app.js", "app.js - Bootstrap"),
        (f"{base_url}/app/js/style.js", "style.js - Štýly"),
        (f"{base_url}/app/js/tag.js", "tag.js - Tagy"),
        (f"{base_url}/app/js/index.js", "index.js - Jazyk"),
    ]

    for url, title in js_files:
        analyze_js(url, title, search_terms)


def analyze_all_html(base_url):
    """Analýza všetkých HTML stránok."""
    html_files = [
        (f"{base_url}/", "Login stránka"),
        (f"{base_url}/main/index", "Main dashboard"),
        (f"{base_url}/index/index", "Index redirect"),
    ]

    for url, title in html_files:
        analyze_html(url, title)


def summarize_findings():
    """Zhrnutie všetkých nájdených endpointov."""
    print("\n" + "=" * 60)
    print("=== ZHRNUTIE ENDPOINTOV ===")

    endpoints = {
        "login": ["/login/userLogin"],
        "style": [
            "/style/getStylesMsg",
            "/style/getStyleMsgs",
            "/style/getStyleMsgById",
            "/style/getDispMsData",
            "/style/updateStyle",
            "/style/addStyle",
            "/style/updateDispMData",
            "/style/getStyleData",
            "/style/queryStyles",
            "/style/cloneStyle",
        ],
        "tag": [
            "/tag/getTagsMsg",
            "/tag/getTagMsgById",
            "/tag/update",
            "/tag/updateTag",
            "/tag/addTag",
            "/tag/deleteTag",
        ],
        "associate": [
            "/associate/getStyleMsgs",
        ],
    }

    for category, eps in endpoints.items():
        print(f"\n  [{category.upper()}]")
        for ep in eps:
            print(f"    {ep}")


if __name__ == "__main__":
    print("=" * 60)
    print("ESL Manager - Konsolidovaný analysis skript")
    print("=" * 60)

    ESL_BASE = "http://192.168.16.251/esls_new"

    # 1. Analýza HTML
    print("\n" + "=" * 60)
    print("=== HTML ANALÝZA ===")
    analyze_all_html(ESL_BASE)

    # 2. Analýza JS
    print("\n" + "=" * 60)
    print("=== JS ANALÝZA ===")
    analyze_all_js(ESL_BASE)

    # 3. Zhrnutie
    summarize_findings()

    print("\n[RESULT] Kľúčové zistenia:")
    print("  1. updateDispMData NIE JE v žiadnom statickom JS súbore")
    print("  2. orderJson NIE JE v žiadnom statickom JS súbore")
    print("  3. app.js je len Bootstrap - nepodstatný")
    print("  4. style.js a tag.js obsahujú API logiku")
    print("  5. index.js je len pre i18n - nepodstatný")
    print("  6. API endpointy sú relatívne voči /esls_new/")
    print("  7. updateDispMData endpoint je dynamicky generovaný alebo v inline skripte")

    print("\n[OK] Analysis skript dokončený.")
