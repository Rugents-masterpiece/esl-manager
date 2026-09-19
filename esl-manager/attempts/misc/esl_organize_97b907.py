#!/usr/bin/env python3
"""Usporiada ESL skripty z /tmp a ~/.hermes/scripts do workspace."""
import os, shutil, hashlib
from pathlib import Path

SRC_TMP = Path("/tmp")
SRC_SCRIPTS = Path("/home/jamailo/.hermes/scripts")
DST = Path("/home/jamailo/workspace/esl-manager")

# Kategórie
CATEGORIES = {
    "login": ["login"],
    "styles": ["style", "styles", "getstyle", "get_styles"],
    "tags": ["tag", "tags", "gettag", "get_tags"],
    "create": ["create", "add", "clone", "new"],
    "update": ["update", "change", "color", "verify"],
    "debug": ["debug"],
    "analysis": ["analyze", "analysis", "inspect"],
    "js": ["js", "javascript", "app", "index", "main"],
    "download": ["download", "find", "fetch"],
    "test": ["test", "verify", "check"],
    "misc": [],
}

def classify(name):
    n = name.lower()
    for cat, keywords in CATEGORIES.items():
        if cat == "misc":
            continue
        if any(k in n for k in keywords):
            return cat
    return "misc"

def unique_name(path, existing):
    name = path.name
    base, ext = os.path.splitext(name)
    h = hashlib.md5(path.read_bytes()[:512]).hexdigest()[:6]
    candidate = f"{base}_{h}{ext}"
    if candidate not in existing:
        return candidate
    # Skús ďalšie
    for i in range(100):
        candidate = f"{base}_{h}_{i}{ext}"
        if candidate not in existing:
            return candidate
    return name

# Zbierame všetky ESL skripty
all_scripts = []
seen = set()

for f in SRC_TMP.glob("esl_*.py"):
    if f.name not in seen:
        all_scripts.append(f)
        seen.add(f.name)

for f in SRC_SCRIPTS.glob("esl_*.py"):
    if f.name not in seen:
        all_scripts.append(f)
        seen.add(f.name)

print(f"Našiel som {len(all_scripts)} unikátnych ESL skriptov")

# Vytvoríme štruktúru
for cat in ["login", "styles", "tags", "create", "update", "debug", "analysis", "js", "download", "test", "misc"]:
    (DST / "attempts" / cat).mkdir(parents=True, exist_ok=True)

(DST / "docs").mkdir(parents=True, exist_ok=True)
(DST / "js-analysis").mkdir(parents=True, exist_ok=True)
(DST / "results").mkdir(parents=True, exist_ok=True)
(DST / "scripts").mkdir(parents=True, exist_ok=True)

# Kopírujeme
moved = 0
for f in sorted(all_scripts):
    cat = classify(f.name)
    dst_dir = DST / "attempts" / cat
    existing = {x.name for x in dst_dir.glob("*.py")}
    dst_name = unique_name(f, existing)
    dst = dst_dir / dst_name
    try:
        shutil.copy2(f, dst)
        moved += 1
    except Exception as e:
        print(f"❌ Chyba: {f.name} -> {e}")

# Kopírujeme hlavné skripty do scripts/
for f in [SRC_SCRIPTS / "esl_manager.py", SRC_SCRIPTS / "esl_cli.py", SRC_SCRIPTS / "esl_tester.py"]:
    if f.exists():
        shutil.copy2(f, DST / "scripts" / f.name)

print(f"✅ Presunuté: {moved} skriptov")

# Zobrazi štruktúru
print("\n📁 Štruktúra:")
for item in sorted(DST.iterdir()):
    if item.is_dir():
        files = list(item.glob("*.py")) + list(item.glob("*.md"))
        if files:
            print(f"  {item.name}/ ({len(files)} súborov)")
            for f in sorted(files)[:3]:
                print(f"    - {f.name}")
            if len(files) > 3:
                print(f"    ... a {len(files)-3} ďalších")
