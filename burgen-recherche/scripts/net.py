"""Gemeinsame Netzfunktionen (nur Standardbibliothek).

Schnell scheitern statt warten: kurze Zeitlimits, kein Wiederholen bei HTTP-4xx, und nach einem
Netzausfall merkt sich das Modul für 30 Minuten, dass die Sandbox offline ist. Folgeaufrufe brechen
dann sofort ab, damit die Recherche mit der Websuche weitermachen kann.
"""

import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Burgenmeier-Recherche/1.0 (Burgrekonstruktion; Python urllib)"
OFFLINE_MARK = os.path.join(tempfile.gettempdir(), "burgen_recherche_offline")
OFFLINE_TTL = 1800


class Offline(RuntimeError):
    pass


def _offline_known():
    try:
        return time.time() - os.path.getmtime(OFFLINE_MARK) < OFFLINE_TTL
    except OSError:
        return False


def _mark_offline(reason):
    try:
        with open(OFFLINE_MARK, "w", encoding="utf-8") as f:
            f.write(str(reason))
    except OSError:
        pass


def get(url, params=None, timeout=15, tries=2, raw=False):
    if _offline_known():
        raise Offline("Kein Netz in der Sandbox (bereits festgestellt). Weiter mit der Websuche.")
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return data if raw else json.loads(data)
        except urllib.error.HTTPError as ex:
            if ex.code in (403, 407):
                _mark_offline(ex)  # in der Sandbox: Proxy verweigert die Domain
                raise Offline(f"Domain gesperrt ({ex.code}). Weiter mit der Websuche.") from ex
            if 400 <= ex.code < 500 and ex.code != 429:
                raise RuntimeError(f"Abruf abgelehnt ({ex.code}): {url[:90]}…") from ex
            last = ex
        except (urllib.error.URLError, OSError) as ex:  # DNS, Verbindung, Zeitüberschreitung
            last = ex
            if k == tries - 1:
                _mark_offline(ex)
                raise Offline(f"Kein Netz in der Sandbox ({ex}). Weiter mit der Websuche.") from ex
        time.sleep(1.0)
    raise RuntimeError(f"Abruf fehlgeschlagen ({url[:90]}…): {last}")
