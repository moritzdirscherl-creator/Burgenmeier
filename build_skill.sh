#!/usr/bin/env sh
# Packt den Skill-Ordner als ZIP zum Hochladen in claude.ai (Einstellungen → Skills).
set -e
cd "$(dirname "$0")"
mkdir -p dist
rm -f dist/burgenmeier.zip
python3 - <<'PY'
import os, zipfile
with zipfile.ZipFile("dist/burgenmeier.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk("burgenmeier"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".pyc"):
                continue
            p = os.path.join(root, f)
            z.write(p, p)
print("dist/burgenmeier.zip")
PY
