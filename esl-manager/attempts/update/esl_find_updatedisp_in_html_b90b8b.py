#!/usr/bin/env python3
"""Najdi updateDispMData v tag.js a index.html."""
import re, urllib.request

ESL_BASE = "http://192.168.16.251/esls_new"

# 1. Analyzuju tag.js
print("[1] Analyzuju tag.js...")
with urllib.request.urlopen(f"{ESL_BASE}/app/js/tag.js", timeout=15) as resp:
    tag_js = resp.read().decode("utf-8", errors="replace")

if "updateDispMData" in tag_js:
    print("    NASHIEL updateDispMData v tag.js!")
    idx = tag_js.find("updateDispMData")
    snippet = tag_js[max(0,idx-500):idx+1500]
    print(f"    Kontext:\n{snippet}")
else:
    print("    updateDispMData NENASHIEL v tag.js")

# 2. Analyzuju index.html po prihlaseni
print("\n[2] Analyzuju index.html...")
import http.cookiejar, hashlib
passwd_md5 = hashlib.md5(b"admin").hexdigest()
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

login_data = {"username": "admin", "passwd": passwd_md5}
body = urllib.parse.urlencode(login_data, encoding="utf-8").encode("utf-8")
req = urllib.request.Request(f"{ESL_BASE}/login/userLogin", data=body, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
req.add_header("X-Requested-With", "XMLHttpRequest")

with opener.open(req, timeout=15) as resp:
    resp.read()

# Skus main/index
print("\n[3] Skusam main/index...")
try:
    with opener.open(f"{ESL_BASE}/main/index", timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"    Length: {len(html)}")
        if "updateDispMData" in html:
            print("    NASHIEL updateDispMData v index.html!")
            idx = html.find("updateDispMData")
            snippet = html[max(0,idx-500):idx+1500]
            print(f"    Kontext:\n{snippet}")
        else:
            print("    updateDispMData NENASHIEL v index.html")
        
        # Hladaj vsetky endpointy v HTML
        urls = set(re.findall(r'["\'](/esls_new/[^"\']+)["\']', html))
        if urls:
            print(f"    Endpointy v index.html ({len(urls)}):")
            for u in sorted(urls):
                print(f"      {u}")
except Exception as e:
    print(f"    Chyba: {e}")

# 3. Skus main.jsp
print("\n[4] Skusam main.jsp...")
try:
    with opener.open(f"{ESL_BASE}/main/index.jsp", timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"    Length: {len(html)}")
        if "updateDispMData" in html:
            print("    NASHIEL updateDispMData v index.jsp!")
            idx = html.find("updateDispMData")
            snippet = html[max(0,idx-500):idx+1500]
            print(f"    Kontext:\n{snippet}")
        else:
            print("    updateDispMData NENASHIEL v index.jsp")
except Exception as e:
    print(f"    Chyba: {e}")

# 4. Skus index.jsp
print("\n[5] Skusam index.jsp...")
try:
    with opener.open(f"{ESL_BASE}/index.jsp", timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"    Length: {len(html)}")
        if "updateDispMData" in html:
            print("    NASHIEL updateDispMData v index.jsp!")
            idx = html.find("updateDispMData")
            snippet = html[max(0,idx-500):idx+1500]
            print(f"    Kontext:\n{snippet}")
        else:
            print("    updateDispMData NENASHIEL v index.jsp")
except Exception as e:
    print(f"    Chyba: {e}")

# 5. Skus style/index.jsp
print("\n[6] Skusam style/index.jsp...")
try:
    with opener.open(f"{ESL_BASE}/style/index.jsp", timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"    Length: {len(html)}")
        if "updateDispMData" in html:
            print("    NASHIEL updateDispMData v style/index.jsp!")
            idx = html.find("updateDispMData")
            snippet = html[max(0,idx-500):idx+1500]
            print(f"    Kontext:\n{snippet}")
        else:
            print("    updateDispMData NENASHIEL v style/index.jsp")
except Exception as e:
    print(f"    Chyba: {e}")

# 6. Skus associate/index.jsp
print("\n[7] Skusam associate/index.jsp...")
try:
    with opener.open(f"{ESL_BASE}/associate/index.jsp", timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"    Length: {len(html)}")
        if "updateDispMData" in html:
            print("    NASHIEL updateDispMData v associate/index.jsp!")
            idx = html.find("updateDispMData")
            snippet = html[max(0,idx-500):idx+1500]
            print(f"    Kontext:\n{snippet}")
        else:
            print("    updateDispMData NENASHIEL v associate/index.jsp")
except Exception as e:
    print(f"    Chyba: {e}")

# 7. Skus all index.html files
print("\n[8] Skusam vsetky index.html...")
paths_to_try = [
    "/index.html",
    "/main/index.html",
    "/style/index.html",
    "/associate/index.html",
    "/tag/index.html",
    "/mms/index.html",
]
for path in paths_to_try:
    try:
        with opener.open(f"{ESL_BASE}{path}", timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            if "updateDispMData" in html:
                print(f"    NASHIEL updateDispMData v {path}!")
                idx = html.find("updateDispMData")
                snippet = html[max(0,idx-500):idx+1500]
                print(f"    Kontext:\n{snippet}")
            else:
                print(f"    {path}: {len(html)} chars, no updateDispMData")
    except Exception as e:
        print(f"    {path}: {e}")
