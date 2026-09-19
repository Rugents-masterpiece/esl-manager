#!/usr/bin/env python3
"""ESL CLI - príkazový riadok pre správu elektronických cenoviek.

Používa ESLManager z esl_manager.py.
"""

import sys
import os
import json
import argparse

# Pridaj cestu k ESLManager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from esl_manager import ESLManager
except ImportError as e:
    print(f"Chyba importu ESLManager: {e}")
    sys.exit(1)


def cmd_list_tags(args):
    """Zobrazí zoznam všetkých tagov."""
    esl = ESLManager()
    try:
        tags = esl.get_tags()
        if not tags:
            print("Žiadne tagy nenaájdené")
            return
        
        print(f"Nájdené {len(tags)} tagov:\n")
        for i, tag in enumerate(tags, 1):
            print(f"Tag #{i}:")
            print(esl.format_tag_info(tag))
            print()
    except Exception as e:
        print(f"Chyba pri načítavaní tagov: {e}")
        sys.exit(1)


def cmd_list_styles(args):
    """Zobrazí zoznam všetkých šablón."""
    esl = ESLManager()
    try:
        styles = esl.get_styles()
        if not styles:
            print("Žiadne šablóny nenaájdené")
            return
        
        print(f"Nájdené {len(styles)} šablón:\n")
        for i, s in enumerate(styles, 1):
            print(f"Šablóna #{i}:")
            print(esl.format_style_info(s))
            print()
    except Exception as e:
        print(f"Chyba pri načítavaní šablón: {e}")
        sys.exit(1)


def cmd_get_style(args):
    """Zobrazí detail šablóny."""
    esl = ESLManager()
    try:
        style = esl.get_style_by_id(args.id)
        print(json.dumps(style, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Chyba pri načítavaní šablóny {args.id}: {e}")
        sys.exit(1)


def cmd_get_style_details(args):
    """Načíta kompletné detaily šablóny (vrátane polí)."""
    esl = ESLManager()
    try:
        details = esl.get_style_details(args.id)
        print(json.dumps(details, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Chyba pri načítavaní detailov šablóny {args.id}: {e}")
        sys.exit(1)


def cmd_list_routers(args):
    """Zobrazí zoznam základných staníc."""
    esl = ESLManager()
    try:
        routers = esl.get_routers()
        if not routers:
            print("Žiadne základné stanice nenaájdené")
            return
        
        print(f"Nájdené {len(routers)} základných staníc:\n")
        for i, r in enumerate(routers, 1):
            print(f"Stanica #{i}:")
            print(json.dumps(r, indent=2, ensure_ascii=False))
            print()
    except Exception as e:
        print(f"Chyba pri načítavaní staníc: {e}")
        sys.exit(1)


def cmd_list_photos(args):
    """Zobrazí zoznam obrázkov."""
    esl = ESLManager()
    try:
        photos = esl.get_photos()
        if not photos:
            print("Žiadne obrázky nenaájdené")
            return
        
        print(f"Nájdené {len(photos)} obrázkov:\n")
        for p in photos:
            print(f"  {p.get('name')}: {p.get('width')}x{p.get('height')} (ID: {p.get('id')})")
    except Exception as e:
        print(f"Chyba pri načítavaní obrázkov: {e}")
        sys.exit(1)


def cmd_preview(args):
    """Stiahne a zobrazí preview šablóny."""
    esl = ESLManager()
    try:
        data = esl.get_style_preview(args.id)
        # Ulož do súboru
        path = os.path.expanduser(f"~/.hermes/scripts/esl_preview_{args.id}.png")
        import base64
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        print(f"Preview šablóny {args.id} uložený: {path}")
    except Exception as e:
        print(f"Chyba pri sťahovaní preview: {e}")
        sys.exit(1)


def cmd_clone(args):
    """Naklonuje šablónu s novým menom."""
    esl = ESLManager()
    try:
        result = esl.clone_style(args.id, args.name)
        print(f"Šablóna naklonovaná: ID={result}")
    except Exception as e:
        print(f"Chyba pri klonovaní šablóny: {e}")
        sys.exit(1)


def cmd_apply(args):
    """Aplikuje šablónu na konkrétny tag."""
    esl = ESLManager()
    try:
        # Načíta JSON s hodnotami polí
        if args.values:
            values = json.loads(args.values)
        else:
            values = {}
        
        update = {
            "mac": args.mac,
            "styleid": args.style_id,
            "mappingtype": 1,
            "ABDisplayFlag": args.ab_flag if hasattr(args, 'ab_flag') else 163,
        }
        update.update(values)
        
        result = esl.update_screen([update])
        print(f"Aktualizácia odoslaná pre MAC {args.mac}: {result}")
    except Exception as e:
        print(f"Chyba pri aplikácii šablóny: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="ESL CLI - správa elektronických cenoviek",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Príkaz")
    
    # list-tags
    subparsers.add_parser("list-tags", help="Zoznam všetkých tagov")
    
    # list-styles
    subparsers.add_parser("list-styles", help="Zoznam všetkých šablón")
    
    # get-style
    p = subparsers.add_parser("get-style", help="Detail šablóny")
    p.add_argument("id", type=int, help="ID šablóny")
    
    # get-style-details
    p = subparsers.add_parser("get-style-details", help="Kompletné detaily šablóny")
    p.add_argument("id", type=int, help="ID šablóny")
    
    # list-routers
    subparsers.add_parser("list-routers", help="Zoznam základných staníc")
    
    # list-photos
    subparsers.add_parser("list-photos", help="Zoznam obrázkov")
    
    # preview
    p = subparsers.add_parser("preview", help="Stiahne preview šablóny")
    p.add_argument("id", type=int, help="ID šablóny")
    
    # clone
    p = subparsers.add_parser("clone", help="Naklonuje šablónu")
    p.add_argument("id", type=int, help="ID zdrojovej šablóny")
    p.add_argument("name", help="Nové meno šablóny")
    
    # apply
    p = subparsers.add_parser("apply", help="Aplikuje šablónu na tag")
    p.add_argument("mac", help="MAC adresa tagu")
    p.add_argument("style_id", type=int, help="ID šablóny")
    p.add_argument("--values", help="JSON s hodnotami polí")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Mapovanie príkazov na funkcie
    commands = {
        "list-tags": cmd_list_tags,
        "list-styles": cmd_list_styles,
        "get-style": cmd_get_style,
        "get-style-details": cmd_get_style_details,
        "list-routers": cmd_list_routers,
        "list-photos": cmd_list_photos,
        "preview": cmd_preview,
        "clone": cmd_clone,
        "apply": cmd_apply,
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()