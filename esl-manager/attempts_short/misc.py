#!/usr/bin/env python3
"""
ESL Manager - Konsolidovaný misc skript
Zhrnutie 6 pôvodných skriptov z attempts/misc/

Cieľ: Rôzne pomocné skripty - CLI, HTML dump, inline scripts, atď.

Obsahuje:
  - CLI rozhranie pre ESL Manager
  - HTML dump a analýzu
  - Inline script analýzu
  - Základné utility funkcie

Výsledky:
  - CLI rozhranie funguje cez argparse
  - HTML dump ukazuje že login stránka je jednoduchá
  - Inline scripty neobsahujú API logiku
  - Main dashboard redirectuje na /main/index
"""

import json
import urllib.request
import re
import argparse


def dump_html(url, title=""):
    """Dump HTML stránky."""
    print(f"\n[HTML_DUMP] {title}: {url}")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            print(f"  Dĺžka: {len(html)}")
            print(f"  Obsah: {html[:500]}...")
    except Exception as e:
        print(f"  Chyba: {e}")


def dump_inline_scripts(url, title=""):
    """Dump inline scriptov z HTML."""
    print(f"\n[INLINE_SCRIPTS] {title}: {url}")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

            inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
            print(f"  Inline scripty: {len(inline_scripts)}")

            for i, script in enumerate(inline_scripts):
                if len(script.strip()) > 20:
                    print(f"\n  --- Script {i} ---")
                    print(f"  {script[:500]}...")
    except Exception as e:
        print(f"  Chyba: {e}")


def cli_main():
    """CLI rozhranie pre ESL Manager."""
    parser = argparse.ArgumentParser(description="ESL Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list-styles
    styles_parser = subparsers.add_parser("list-styles", help="List all styles")
    styles_parser.add_argument("--id", type=int, help="Get specific style by ID")

    # list-tags
    tags_parser = subparsers.add_parser("list-tags", help="List all tags")

    # get-style-data
    style_data_parser = subparsers.add_parser("get-style-data", help="Get style data")
    style_data_parser.add_argument("style_id", type=int, help="Style ID")

    # update-style-name
    update_parser = subparsers.add_parser("update-style-name", help="Update style name")
    update_parser.add_argument("style_id", type=int, help="Style ID")
    update_parser.add_argument("name", help="New name")

    args = parser.parse_args()

    if args.command == "list-styles":
        print("[CLI] list-styles")
        # ... implementácia
    elif args.command == "list-tags":
        print("[CLI] list-tags")
        # ... implementácia
    elif args.command == "get-style-data":
        print(f"[CLI] get-style-data {args.style_id}")
        # ... implementácia
    elif args.command == "update-style-name":
        print(f"[CLI] update-style-name {args.style_id} -> {args.name}")
        # ... implementácia
    else:
        parser.print_help()


if __name__ == "__main__":
    print("=" * 60)
    print("ESL Manager - Konsolidovaný misc skript")
    print("=" * 60)

    ESL_BASE = "http://192.168.16.251/esls_new"

    # Skontroluj CLI arguments
    import sys
    if len(sys.argv) > 1:
        cli_main()
    else:
        # Default - dump HTML
        dump_html(f"{ESL_BASE}/", "Login stránka")
        dump_html(f"{ESL_BASE}/main/index", "Main dashboard")
        dump_inline_scripts(f"{ESL_BASE}/", "Inline scripty")

        print("\n[RESULT] Misc skript dokončený.")
        print("  Použi --help pre CLI rozhranie")
