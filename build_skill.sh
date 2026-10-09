#!/usr/bin/env sh
# Packt die Skill-Ordner als ZIPs zum Hochladen in claude.ai (Einstellungen → Skills).
set -e
cd "$(dirname "$0")"
mkdir -p dist
python3 - <<'PY'
import os, zipfile
for skill in ("burgenmeier", "burgen-recherche"):
    out = f"dist/{skill}.zip"
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(skill):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if not f.endswith(".pyc"):
                    z.write(os.path.join(root, f))
    print(out)
PY
