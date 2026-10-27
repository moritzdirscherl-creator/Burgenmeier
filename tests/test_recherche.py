import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "burgen-recherche", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "burgenmeier", "scripts"))

import castle_lib  # noqa: E402
import commons  # noqa: E402
import dossier  # noqa: E402
import validate  # noqa: E402
import wikidata  # noqa: E402

# Nachgebildete API-Antworten im Format der MediaWiki-/Wikibase-API
WD_SEARCH = {"search": [
    {"id": "Q1", "label": "Falkenstein", "description": "Gemeinde in Bayern"},
    {"id": "Q42", "label": "Burg Falkenstein", "description": "Burgruine im Landkreis X"}]}
WD_ENTITY = {"entities": {"Q42": {
    "labels": {"de": {"value": "Burg Falkenstein"}, "la": {"value": "Castrum Falconis"}},
    "descriptions": {"de": {"value": "Burgruine"}},
    "aliases": {"de": [{"value": "Veste Falkenstein"}]},
    "sitelinks": {"dewiki": {"title": "Burg Falkenstein (X)"}, "commonswiki": {"title": "Category:Burg Falkenstein"}},
    "claims": {
        "P625": [{"mainsnak": {"datavalue": {"value": {"latitude": 49.1234567, "longitude": 11.7654321}}}}],
        "P2044": [{"mainsnak": {"datavalue": {"value": {"amount": "+512"}}}}],
        "P571": [{"mainsnak": {"datavalue": {"value": {"time": "+1150-00-00T00:00:00Z", "precision": 7}}}}],
        "P131": [{"mainsnak": {"datavalue": {"value": {"id": "Q99"}}}}],
        "P373": [{"mainsnak": {"datavalue": {"value": "Burg Falkenstein (X)"}}}],
        "P3311": [{"mainsnak": {"datavalue": {"value": "Falkenstein Grundriss.png"}}}],
    }}}}
WD_LABELS = {"entities": {"Q99": {"labels": {"de": {"value": "Landkreis X"}}}}}
COMMONS = {"query": {"pages": {
    "1": {"title": "File:Falkenstein Merian 1644.jpg", "imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/thumb/a.jpg", "url": "https://upload.wikimedia.org/a.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Falkenstein_Merian_1644.jpg", "mime": "image/jpeg",
        "extmetadata": {"ImageDescription": {"value": "<p>Kupferstich aus der <i>Topographia</i></p>"},
                        "Artist": {"value": "<a href='x'>Matthäus Merian</a>"},
                        "DateTimeOriginal": {"value": "1644"}, "LicenseShortName": {"value": "Public domain"}}}]},
    "2": {"title": "File:Falkenstein Grundriss.png", "imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/thumb/b.png", "descriptionurl": "https://commons.wikimedia.org/wiki/File:F_G.png",
        "mime": "image/png", "extmetadata": {"ImageDescription": {"value": "Grundriss nach Piper"},
                                             "LicenseShortName": {"value": "CC BY-SA 4.0"}}}]},
    "3": {"title": "File:Falkenstein 2019.jpg", "imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/thumb/c.jpg", "mime": "image/jpeg",
        "extmetadata": {"DateTimeOriginal": {"value": "2019-05-01"}, "LicenseShortName": {"value": "CC BY 4.0"}}}]},
}}}


@pytest.fixture
def fake_net(monkeypatch):
    def get(url, params=None, timeout=40, tries=3, raw=False):
        if raw:
            return b"\x89PNG fake"
        p = params or {}
        if "wikidata" in url:
            if p.get("action") == "wbsearchentities":
                return WD_SEARCH
            if p.get("ids") == "Q42":
                return WD_ENTITY
            return WD_LABELS
        return COMMONS
    import net
    monkeypatch.setattr(net, "get", get)


def test_wikidata_facts(fake_net):
    cands = wikidata.search("Falkenstein")
    assert [c["burgartig"] for c in cands] == [False, True]
    f = wikidata.entity("Q42")
    assert f["lat"] == 49.123457 and f["hoehe"] == 512
    assert f["gruendung"] == "12. Jh."
    assert "Castrum Falconis" in f["namensvarianten"] and "Veste Falkenstein" in f["namensvarianten"]
    assert f["liegt_in"] == ["Landkreis X"]
    assert f["grundrissbild_url"].endswith("File:Falkenstein_Grundriss.png")
    assert f["wikipedia"]["de"].startswith("https://de.wikipedia.org/wiki/Burg_Falkenstein")
    assert "commons" not in f["wikipedia"]


def test_wikidata_into_dossier(fake_net, tmp_path):
    p = str(tmp_path / "q.json")
    wikidata.to_dossier(wikidata.entity("Q42"), p)
    d = dossier.load(p)
    assert d["burg"]["lat"] == 49.123457 and d["burg"]["wikidata"] == "Q42"
    assert [s["id"] for s in d["sources"]] == ["Q1", "Q2"]  # Wikidata + de-Wikipedia
    wikidata.to_dossier(wikidata.entity("Q42"), p)  # zweimal -> keine Dubletten
    assert len(dossier.load(p)["sources"]) == 2


def test_commons_classification_and_dossier(fake_net, tmp_path):
    files = commons.search("Falkenstein")
    by = {f["commons_titel"]: f for f in files}
    assert by["Falkenstein Merian 1644.jpg"]["type"] == "illustration"
    assert by["Falkenstein Merian 1644.jpg"]["author"] == "Matthäus Merian"
    assert by["Falkenstein Merian 1644.jpg"]["year"] == 1644
    assert by["Falkenstein Grundriss.png"]["type"] == "plan"
    assert by["Falkenstein 2019.jpg"]["type"] == "photo"
    commons.download(files, str(tmp_path / "bilder"))
    assert all(os.path.exists(f["file"]) for f in files if f["type"] != "photo")
    p = str(tmp_path / "q.json")
    assert commons.to_dossier(files, p) == 2  # Foto ohne --fotos nicht übernommen
    d = dossier.load(p)
    assert all(s["viewed"] is False for s in d["sources"])
    assert {s["license"] for s in d["sources"]} == {"Public domain", "CC BY-SA 4.0"}


def test_dossier_cli_flow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run = dossier.main
    assert run(["init", "Burg Test", "-o", "q.json"]) == 0
    run(["setze", "q.json", "lat=50.1", "lon=8.2", "lage=spur", "relief=70", "richtung=120", "zieldatum=1380",
         "namensvarianten=Veste Test, Castrum Test"])
    run(["add", "q.json", "--type", "plan", "--title", "Grundriss", "--author", "Piper", "--year", "1912", "--viewed"])
    run(["add", "q.json", "--type", "text", "--title", "Teilungsvertrag", "--year", "1412", "--signatur", "UB Nr. 3"])
    run(["befund", "q.json", "Q2", "--bauteil", "Kapelle", "--aussage", "genannt", "--zitat", "die capelle"])
    run(["ereignis", "q.json", "--jahr", "1150", "--text", "Ersterwähnung", "--quelle", "Q2"])
    run(["luecke", "q.json", "Dachform unbelegt"])
    d = dossier.load("q.json")
    errs, hints = dossier.check(d)
    assert errs == []
    assert any("viewed=false" in h for h in hints)       # Befund ohne Sichtung wird angemahnt
    assert any("Abbildung" in h or "abbildung" in h.lower() for h in hints)
    md = dossier.render(d)
    assert "Kapelle" in md and "Dachform unbelegt" in md and "nicht selbst gesichtet" in md
    assert run(["castle", "q.json", "-o", "castle.json"]) == 0
    with pytest.raises(SystemExit):  # nie überschreiben
        run(["castle", "q.json", "-o", "castle.json"])


def test_check_flags_unverifiable_sources():
    d = dossier.new("X")
    dossier.add_source(d, {"type": "text", "title": "irgendeine Urkunde"})
    errs, _ = dossier.check(d)
    assert any("nicht nachprüfbar" in e for e in errs) and any("Koordinaten" in e for e in errs)


def test_skeleton_feeds_burgenmeier(tmp_path):
    """Gerüst aus dem Dossier + ein Element ergibt eine gültige castle.json für burgenmeier."""
    d = dossier.new("Burg Test")
    d["burg"].update({"lat": 50.1, "lon": 8.2, "lage": "spur", "zieldatum": 1380})
    dossier.add_source(d, {"type": "plan", "title": "Grundriss", "author": "Piper", "year": 1912, "viewed": True})
    c = dossier.to_castle(d)
    c["elements"].append({"id": "turm", "type": "tower", "center": [0, 0], "radius": 5, "height": 20,
                          "evidence": {"confidence": "gesichert", "sources": ["Q1"]}})
    p = tmp_path / "castle.json"
    p.write_text(json.dumps(c, ensure_ascii=False))
    errors, _ = validate.validate(castle_lib.load_castle(str(p)))
    assert errors == []


def test_offline_fails_fast(monkeypatch, tmp_path):
    import time
    import urllib.request

    import net
    monkeypatch.setattr(net, "OFFLINE_MARK", str(tmp_path / "offline"))
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise OSError("Network is unreachable")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    with pytest.raises(net.Offline):
        net.get("https://www.wikidata.org/w/api.php")
    n = len(calls)
    with pytest.raises(net.Offline):  # zweiter Aufruf: sofort, ohne Netzversuch
        net.get("https://commons.wikimedia.org/w/api.php")
    assert len(calls) == n


def test_commons_skips_photo_downloads(fake_net, tmp_path):
    files = commons.search("Falkenstein")
    commons.download(files, str(tmp_path / "q"))
    by_type = {f["type"]: f for f in files}
    assert by_type["photo"].get("file") is None
    assert os.path.exists(by_type["illustration"]["file"])
