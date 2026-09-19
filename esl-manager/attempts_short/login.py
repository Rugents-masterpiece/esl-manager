#!/usr/bin/env python3
"""
ESL Manager - Konsolidovaný login skript
Zhrnutie 7 pôvodných skriptov z attempts/login/

Cieľ: Prihlásiť sa do ESL dashboardu a získať validný JSESSIONID cookie.

Endpointy:
  POST /esls_new/login/userLogin - Prihlásenie
  GET  /esls_new/               - Login stránka (analýza)

Formát login requestu:
  - Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  - X-Requested-With: XMLHttpRequest
  - Body: username=admin&passwd=<MD5 hash>
  - Password: "admin" -> MD5 hash

Výsledky testov:
  - Login úspešný, server vracia JSESSIONID cookie
  - Login stránka obsahuje form s action="/login/userLogin"
  - Password sa hashuje MD5 v JavaScripte (client-side)
  - Po prihlásení sa presmeruje na /main/index

Kľúčové zistenia z analýzy:
  1. Login endpoint je /login/userLogin (nie /esls_new/login/userLogin)
  2. Heslo "admin" sa hashuje na MD5 na strane klienta
  3. Session cookie sa volá JSESSIONID
  4. Po prihlásení sa načítajú JS súbory: app.js, style.js, tag.js, index.js
  5. Všetky API endpointy sú relatívne voči /esls_new/
"""

import json
import urllib.request
import urllib.parse
import hashlib
import http.cookiejar

ESL_BASE = "http://192.168.16.251/esls_new"
USERNAME = "admin"
PASSWORD = "admin"  # MD5 hash sa počíta dynamicky


def login():
    """Prihlásenie a vrátenie openera s platnou session."""
    passwd_md5 = hashlib.md5(PASSWORD.encode()).hexdigest()
    data = {"username": USERNAME, "passwd": passwd_md5}
    body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")

    req = urllib.request.Request(
        f"{ESL_BASE}/login/userLogin",
        data=body,
        method="POST"
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    req.add_header("X-Requested-With", "XMLHttpRequest")

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    with opener.open(req, timeout=15) as resp:
        status = resp.status
        raw = resp.read()
        print(f"[LOGIN] Status: {status}")
        print(f"[LOGIN] Response: {repr(raw[:200])}")

    # Získaj JSESSIONID
    session_id = None
    for cookie in cj:
        if cookie.name == "JSESSIONID":
            session_id = cookie.value
            print(f"[LOGIN] JSESSIONID: {session_id[:20]}...")
            break

    return opener, session_id


def analyze_login_page():
    """Analýza login stránky - nájde form action, inputy, script src."""
    print("\n[ANALYSIS] Analyzing login page...")
    req = urllib.request.Request(f"{ESL_BASE}/")
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"  HTML length: {len(html)}")

        # Nájdi form action
        import re
        forms = re.findall(r'<form[^>]*action=["\']?([^"\'>\s]*)["\']?', html)
        print(f"\n[FORMS] {len(forms)} form(s):")
        for f in forms:
            print(f"  action={f}")

        # Nájdi inputy
        inputs = re.findall(r'<input[^>]*>', html)
        print(f"\n[INPUTS] {len(inputs)} input(s):")
        for inp in inputs:
            print(f"  {inp}")

        # Nájdi script src
        scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
        print(f"\n[SCRIPTS] {len(scripts)} script(s):")
        for s in scripts:
            print(f"  src={s}")


if __name__ == "__main__":
    print("=" * 60)
    print("ESL Manager - Konsolidovaný login skript")
    print("=" * 60)

    # 1. Analyzuj login stránku
    analyze_login_page()

    # 2. Prihlás sa
    print("\n" + "=" * 60)
    opener, session_id = login()

    # 3. Over session - zisti zoznam štýlov
    print("\n" + "=" * 60)
    print("[VERIFY] Overing session with getStyleMsgs...")
    req = urllib.request.Request(f"{ESL_BASE}/associate/getStyleMsgs?currentPage=0&pageSize=5")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    with opener.open(req, timeout=15) as resp:
        raw = resp.read()
        styles = json.loads(raw)
        print(f"  Styles count: {len(styles.get('datalist', []))}")
        for s in styles.get("datalist", []):
            print(f"    ID {s['id']}: {s.get('name', '?')}")

    print("\n[OK] Login successful, session verified.")
