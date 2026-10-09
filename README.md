# Burgenmeier

Ein **Claude-Skill**, der aus Ruinenplänen, alten Illustrationen und Primärquellentexten ein plausibles
**Low-Poly-3D-Modell** einer mittelalterlichen Burg samt ihrer damaligen Umgebung erzeugt. Alternativ
entsteht eine **Zeichnung aus gewählter Perspektive**. Standort, Gelände und historische Umgebung
recherchiert Claude selbst. Jedes Bauteil trägt seine Befundstufe (gesichert / wahrscheinlich / Analogie /
Annahme) und seine Quellen.

| Vogelschau (Federzeichnung) | Grundriss nach Befundlage | Interaktiver 3D-Viewer |
|---|---|---|
| ![Vogelschau](docs/vogelschau.jpg) | ![Grundriss](docs/grundriss_befund.jpg) | ![Viewer](docs/viewer.jpg) |

*Abgebildet ist die fiktive „Musterburg“ aus `burgenmeier/examples/`.*

## So funktioniert es

```
Pläne · Bilder · Texte ──► Claude (liest Bilder, wertet Quellen aus, recherchiert per Websuche)
                                   │
                                   ▼
                            castle.json  ◄── strukturierte, belegte Burgbeschreibung
                                   │
           ┌───────────────┬───────┴────────┬──────────────────┐
           ▼               ▼                ▼                  ▼
   build_model.py     draw_view.py     report.py          plan.py overlay
   GLB/OBJ + Viewer   SVG/PNG-Zeichnung  Quellenbericht   Kontrolle auf dem Plan
```

Claude übernimmt die Interpretation, die Skripte die Geometrie. Dadurch sind Modell und Zeichnungen
reproduzierbar und konsistent. Ändert man eine Zahl in `castle.json`, ändern sich alle Ausgaben gleich.

## Installation in claude.ai (Pro, Max, Team, Enterprise)

1. ZIP bauen: `./build_skill.sh` → `dist/burgenmeier.zip` (oder den Ordner `burgenmeier/` selbst zippen).
2. In claude.ai unter **Einstellungen → Funktionen** die **Codeausführung / Dateierstellung** aktivieren.
3. Dort unter **Skills** die ZIP-Datei hochladen und den Skill einschalten.
4. *(Optional, empfohlen)* Für echte Höhendaten und OpenStreetMap braucht die Sandbox Netzzugriff. In den
   Einstellungen zur Codeausführung die Domains `s3.amazonaws.com`, `overpass-api.de`, `www.wikidata.org`
   und `nominatim.openstreetmap.org` freigeben. Ohne Netz funktioniert alles weiterhin, das Gelände wird
   dann aus der Recherche prozedural erzeugt. Claudes eigene **Websuche** sollte ebenfalls an sein.
5. *(Optional)* Ein **Projekt** „Burgenmeier“ anlegen und dort Pläne, Quellen und Fotos als Projektwissen
   ablegen. Dann starten alle Chats mit diesem Material.

Die genaue Bezeichnung der Menüpunkte kann sich ändern. Gesucht sind die Bereiche für Skills und für
Codeausführung.

## Benutzung im Chat

> Rekonstruiere Burg Hohenstein um 1400. Anbei der Grundriss aus dem Inventarband (Maßstab 1:500), eine
> Ansicht von 1630 und der Auszug aus dem Urbar. Ich hätte gern eine Vogelschau von Südwesten und das
> 3D-Modell.

Claude geht dann so vor:

1. Material sichten; den Plan mit einem Pixelraster vermessen.
2. Koordinaten, Gelände und Umgebung recherchieren und auf das Zieldatum zurückprojizieren.
3. `castle.json` schreiben und validieren.
4. Zeichnung, GLB, Viewer und Quellenbericht erzeugen und das Ergebnis selbst kontrollieren.
5. Erklären, was belegt ist und was nicht, und welches Material die Unsicherheit am stärksten senken würde.

Danach kann man im Chat nachsteuern, z. B. „Bergfried mit Zinnenkranz statt Helm“, „Ansicht wie auf der
Vedute von 1630“ oder „nur die Burg, ohne Umgebung, als Grundriss“.

## Lokale Nutzung (ohne Claude)

Benötigt Python 3.9+ mit `numpy` und `Pillow`.

```bash
S=burgenmeier/scripts
python $S/validate.py   burgenmeier/examples/beispiel_castle.json
python $S/build_model.py burgenmeier/examples/beispiel_castle.json --glb burg.glb --obj burg.obj --html burg_3d.html
python $S/draw_view.py  burgenmeier/examples/beispiel_castle.json --view vogelschau -o burg.svg --png burg.png
python $S/draw_view.py  burgenmeier/examples/beispiel_castle.json --azimuth 230 --elevation 20 --focus alles --png umgebung.png
python $S/report.py     burgenmeier/examples/beispiel_castle.json -o bericht.md
python $S/geo.py geocode "Burg Eltz"               # Koordinaten
python $S/geo.py terrain meine_burg.json           # echtes Höhenmodell
python $S/geo.py osm meine_burg.json               # heutige Umgebung als Rohmaterial
python $S/plan.py grid plan.png                    # Raster zum Ablesen von Plankoordinaten
```

Tests: `pip install pytest && python -m pytest tests`

## Aufbau

```
burgenmeier/              ← der Skill (wird gezippt)
  SKILL.md                Arbeitsanleitung für Claude
  reference/              Schema, Typologie & Richtmaße, Umgebung, Quellenkritik
  scripts/                castle_lib (Kern), build_model, draw_view, geo, plan, validate, report
  templates/viewer.html   Three.js-Viewer (Szene wird eingebettet)
  examples/               fiktive Beispielburg
tests/                    pytest
build_skill.sh            erzeugt dist/burgenmeier.zip
```

## Grenzen

- Die Modelle sind **plausibel, nicht wahr**. Die Qualität hängt am Quellenmaterial; die Befundfärbung
  zeigt das ehrlich an.
- Höhenmodelle zeigen das **heutige** Gelände, typischerweise in 5–30 m Auflösung. Kleine Felsen,
  verfüllte Gräben und moderne Eingriffe sind nicht korrigiert. Die Grabenelemente übernehmen das teilweise.
- Low-Poly ist Absicht: keine Fenster, kein Bauschmuck, Dächer als einfache Grundformen.
- Bauten bekommen Wände auf ganzer Footprint-Fläche; Innenhöfe in Gebäuden muss man über mehrere Elemente
  modellieren.
