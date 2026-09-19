#!/usr/bin/env python3
"""Klonovanie style 146 a zmena farby textov na cervenu."""
import sys, json
sys.path.insert(0, '/home/jamailo/.hermes/scripts')
from esl_manager import ESLManager

m = ESLManager()

# 1. Ziskaj detail style 146
print("[1] Ziskujem detail style 146...")
style_146 = m.get_style_by_id(146)
print(f"    Nazov: {style_146.get('name', 'N/A')}")
print(f"    ID: {style_146.get('id')}")

# 2. Ziskaj orderJson (pole) zo style 146
print("\n[2] Ziskujem orderJson zo style 146...")
order_json_146 = m.get_disp_ms_data(146)
print(f"    Pocet polov: {len(order_json_146)}")
for f in order_json_146:
    print(f"      - {f.get('mpname')} ({f.get('name')}): '{f.get('text')[:50]}' farba={f.get('style', {}).get('color', 'N/A')}")

# 3. Naklonej style 146
print("\n[3] Klonujem style 146...")
new_id = m.clone_style(146, f"Kopia_{style_146.get('name', '146')}_red")
print(f"    Nova ID: {new_id}")

# 4. Ziskaj orderJson z noveho style
print(f"\n[4] Ziskujem orderJson z noveho style {new_id}...")
order_json_new = m.get_disp_ms_data(new_id)
print(f"    Pocet polov: {len(order_json_new)}")

# 5. Zmen vsetky texty na cervenu farbu
print("\n[5] Menim farby textov na cervenu (#ff0000)...")
changed = 0
for field in order_json_new:
    if isinstance(field, dict) and field.get("type") == "text":
        style_obj = field.get("style", {})
        if style_obj:
            old_color = style_obj.get("color", "N/A")
            style_obj["color"] = "#ff0000"
            field["style"] = style_obj
            changed += 1
            print(f"      - {field.get('mpname')}: {old_color} -> #ff0000")

print(f"    Zmenenych polov: {changed}")

# 6. Aktualizuj style na serveri
print(f"\n[6] Aktualizujem style {new_id} na serveri...")
result = m.update_style(new_id, order_json_new)
print(f"    Response: {repr(result[:100]) if result else 'prazdny'}")

print("\n[DOKONCENE]")
