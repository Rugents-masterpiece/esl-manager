#!/usr/bin/env python3
"""
ESL Manager - Konsolidovaný skript pre prácu s tagmi
Zhrnutie 6 pôvodných skriptov z attempts/tags/

Cieľ: Získať, analyzovať a aktualizovať tagy na ESL serveri.

Endpointy:
  POST /esls_new/tag/getTagsMsg      - Zoznam tagov
  POST /esls_new/tag/getTagMsgById   - Detail tagu podľa ID
  POST /esls_new/tag/update          - Aktualizácia tagu
  POST /esls_new/tag/updateTag       - Aktualizácia tagu (alternatívny)
  POST /esls_new/tag/addTag          - Vytvorenie nového tagu
  POST /esls_new/tag/deleteTag       - Vymazanie tagu

Výsledky testov:
  - getTagsMsg vracia zoznam tagov s metadátami
  - getTagMsgById vracia detail tagu
  - tag/update a tag/updateTag vracajú "true" alebo "0"
  - tag/addTag vracia "true" pri úspechu
  - tag.js používa ajaxSubmit pre form data s contentType: 'application/json'
  - aj keď contentType je JSON, data sú form-encoded (serialize())

Kľúčové zistenia z analýzy tag.js:
  1. Všetky tag endpointy sú relatívne: /tag/getTagsMsg, /tag/update, atď.
  2. ajaxSubmit používa $('#modifyTagForm).serialize() - form-encoded data
  3. contentType je 'application/json' ale data sú form-encoded
  4. tag/update očakáva parametre: id, name, descriptor, atď.
  5. tag/updateTag je alternatívny endpoint s rovnakou funkcionalitou
"""

import json
import urllib.request
import urllib.parse
import hashlib
import http.cookiejar

ESL_BASE = "http://192.168.168.251/esls_new"
USERNAME = "admin"
PASSWORD = "admin"


def make_request(method, path, data=None, content_type="application/x-www-form-urlencoded; charset=UTF-8"):
    """Urobi request a vrati detailne info."""
    url = f"{ESL_BASE}{path}"
    body = None
    if data:
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
        elif isinstance(data, str):
            body = data.encode("utf-8")
        elif isinstance(data, bytes):
            body = data

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", content_type)
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Accept", "*/*")
    req.add_header("Origin", ESL_BASE)
    req.add_header("Referer", f"{ESL_BASE}/")

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    try:
        with opener.open(req, timeout=30) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace").strip()
            return {
                "status": resp.status,
                "text": text[:500],
                "text_full": text,
                "opener": opener,
            }
    except urllib.error.HTTPError as e:
        raw = e.read()
        text = raw.decode("utf-8", errors="replace").strip()
        return {
            "status": e.code,
            "text": text[:500],
            "text_full": text,
            "error": True,
            "opener": opener,
        }


def get_tags(opener):
    """Získaj zoznam všetkých tagov."""
    print("[GET_TAGS] Načítavam zoznam tagov...")
    result = make_request("POST", "/tag/getTagsMsg", {"currentPage": "0", "pageSize": "200"})
    raw_text = result["text_full"]

    tags = None
    if raw_text.startswith('"') and raw_text.endswith('"'):
        inner = raw_text[1:-1].replace('\\"', '"')
        try:
            tags = json.loads(inner)
        except:
            pass
    elif raw_text.startswith('['):
        try:
            tags = json.loads(raw_text)
        except:
            pass

    if tags and isinstance(tags, list):
        print(f"  Počet tagov: {len(tags)}")
        for t in tags:
            print(f"    ID {t['id']}: {t.get('name', '?')}")
    elif isinstance(tags, dict):
        datalist = tags.get("datalist", [])
        print(f"  Počet tagov: {len(datalist)}")
        for t in datalist:
            print(f"    ID {t['id']}: {t.get('name', '?')}")
    else:
        print(f"  Nemôžem parsovať: {raw_text[:200]}")

    return tags


def get_tag_detail(tag_id, opener):
    """Získaj detail tagu podľa ID."""
    print(f"[GET_DETAIL] Načítavam detail tagu {tag_id}...")
    result = make_request("POST", "/tag/getTagMsgById", {"id": str(tag_id)})
    raw_text = result["text_full"]

    if raw_text.startswith('"') and raw_text.endswith('"'):
        inner = raw_text[1:-1].replace('\\"', '"')
        try:
            tag_data = json.loads(inner)
            print(f"  Tag data: {json.dumps(tag_data, ensure_ascii=False, indent=2)[:500]}")
            return tag_data
        except:
            pass

    print(f"  Response: {raw_text[:300]}")
    return None


def update_tag(tag_id, name, opener):
    """Aktualizuj tag."""
    print(f"[UPDATE_TAG] Aktualizujem tag {tag_id} na '{name}'...")
    update_data = {
        "id": str(tag_id),
        "name": name,
        "descriptor": "Rudo",
        "type": "1"
    }
    result = make_request("POST", "/tag/update", update_data)
    print(f"  Status: {result['status']}, Response: {result['text'][:200]}")
    return result


def update_tag_alt(tag_id, name, opener):
    """Aktualizuj tag cez alternatívny endpoint."""
    print(f"[UPDATE_TAG_ALT] Aktualizujem tag {tag_id} cez tag/updateTag...")
    update_data = {
        "id": str(tag_id),
        "name": name,
        "descriptor": "Rudo",
        "type": "1"
    }
    result = make_request("POST", "/tag/updateTag", update_data)
    print(f"  Status: {result['status']}, Response: {result['text'][:200]}")
    return result


def add_tag(name, opener):
    """Vytvor nový tag."""
    print(f"[ADD_TAG] Vytváram nový tag '{name}'...")
    add_data = {
        "name": name,
        "descriptor": "Rudo",
        "type": "1"
    }
    result = make_request("POST", "/tag/addTag", add_data)
    print(f"  Status: {result['status']}, Response: {result['text'][:200]}")
    return result


def analyze_tag_js():
    """Analýza tag.js - nájdi endpointy a logiku."""
    print("\n[ANALYSIS] Analyzujem tag.js...")
    try:
        with urllib.request.urlopen(f"{ESL_BASE}/app/js/tag.js", timeout=15) as resp:
            tag_js = resp.read().decode("utf-8", errors="replace")
            print(f"  Dĺžka: {len(tag_js)}")

            import re
            # Nájdi všetky endpointy
            endpoints = set(re.findall(r'["\'](/[^"\']*tag/[^"\']+)["\']', tag_js))
            print(f"\n  Endpointy v tag.js ({len(endpoints)}):")
            for ep in sorted(endpoints):
                print(f"    {ep}")

            # Nájdi ajaxSubmit volania
            ajax_calls = re.findall(r'ajaxSubmit\([^)]+\)', tag_js)
            print(f"\n  ajaxSubmit volania: {len(ajax_calls)}")
            for call in ajax_calls[:3]:
                print(f"    {call[:200]}")

            # Nájdi contentType
            content_types = re.findall(r'contentType:\s*["\']([^"\']+)["\']', tag_js)
            print(f"\n  contentType hodnoty: {set(content_types)}")

    except Exception as e:
        print(f"  Chyba: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("ESL Manager - Konsolidovaný tagy skript")
    print("=" * 60)

    # 1. Login
    passwd_md5 = hashlib.md5(PASSWORD.encode()).hexdigest()
    login_data = {"username": USERNAME, "passwd": passwd_md5}
    result = make_request("POST", "/login/userLogin", login_data)
    print(f"[LOGIN] Status: {result['status']}")
    opener = result["opener"]

    # 2. Získaj zoznam tagov
    tags = get_tags(opener)

    # 3. Analyzuj tag.js
    analyze_tag_js()

    # 4. Detail tagu (ak existuje)
    if tags and isinstance(tags, list) and len(tags) > 0:
        first_tag = tags[0]
        if isinstance(first_tag, dict) and "id" in first_tag:
            print("\n" + "=" * 60)
            print("=== DETAIL TAGU ===")
            get_tag_detail(first_tag["id"], opener)

    print("\n[OK] Tagy skript dokončený.")
