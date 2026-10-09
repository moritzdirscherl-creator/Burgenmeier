"""Gemeinsame Netzfunktionen (nur Standardbibliothek)."""

import json
import time
import urllib.parse
import urllib.request

UA = "Burgenmeier-Recherche/1.0 (Burgrekonstruktion; Python urllib)"


def get(url, params=None, timeout=40, tries=3, raw=False):
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return data if raw else json.loads(data)
        except Exception as ex:  # vorübergehende Fehler erneut versuchen
            last = ex
            time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"Abruf fehlgeschlagen ({url[:90]}…): {last}")
