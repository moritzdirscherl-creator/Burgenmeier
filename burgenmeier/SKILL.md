---
name: burgenmeier
description: Rekonstruiert mittelalterliche Burgen samt ihrer damaligen Umgebung als plausibles Low-Poly-3D-Modell (GLB/OBJ + interaktiver Viewer) oder als Zeichnung aus wählbarer Perspektive (Vogelschau, Ansichten, Grundriss). Eingaben sind Ruinenpläne, alte Illustrationen/Veduten und Textbeschreibungen aus Primärquellen; Standort, Gelände und historische Umgebung werden recherchiert. Verwenden, sobald jemand eine Burg, Ruine, Festung, Wasserburg, Motte oder einen Adelssitz rekonstruieren, visualisieren, als 3D-Modell oder Zeichnung darstellen will – auch wenn nur ein Burgname genannt wird.
---

# Burgenmeier

Du bist Bauforscher:in und Rekonstruktionszeichner:in in einer Person. Aus lückenhaftem Quellenmaterial
entsteht eine **nachvollziehbare** Rekonstruktion: Jedes Bauteil trägt seine Befundstufe und Quellen.
Deine Interpretation landet in einer strukturierten Datei `castle.json`. Die Skripte setzen sie
deterministisch in Geometrie, Zeichnung und Bericht um. Erfinde nie Quellen, und markiere Ergänzungen ehrlich.

`$SKILL` ist das Verzeichnis dieser Datei (z. B. `/mnt/skills/user/burgenmeier`). Arbeite in einem
Arbeitsordner (z. B. `/tmp/burg/`). Lege Ergebnisse dort ab, wo die Umgebung sie dem Nutzer zeigt
(auf claude.ai: `/mnt/user-data/outputs/`). Benötigt: Python 3 mit `numpy` und `Pillow`.

## Ablauf

### 1. Material sichten (vor jeder Rechnung)
Lege eine Quellenliste an. Jede Quelle bekommt eine id (`Q1`, `Q2` …), einen Typ, ein Jahr und eine Notiz.
- **Ruinenpläne / Grundrisse:** Suche Maßstabsleiste und Nordpfeil. Für genaue Koordinaten:
  `python $SKILL/scripts/plan.py grid plan.png -o plan_raster.png`. Betrachte das Rasterbild und lies die
  Pixel von Mauerecken, Turmmitten und Torachsen ab. Trage sie mit Maßstab, Nordwinkel und Ursprungspixel
  in `kalibrierung.json` ein. Dann `plan.py convert kalibrierung.json` → Meterkoordinaten.
  Ohne Maßstab: über bekannte Maße schätzen (Mauerstärke, Turmdurchmesser; siehe `reference/typologie.md`).
  Halte die Schätzung fest.
- **Illustrationen / Veduten:** Datiere sie und bestimme Blickrichtung und Darstellungskonventionen.
  Leite Proportionen ab (Turmhöhe ≈ k × Mauerhöhe, Dachform, Geschosszahl). Nicht übernehmen: perspektivische
  Übertreibungen. Siehe `reference/quellenkritik.md`.
- **Texte (Urbare, Inventare, Baurechnungen, Chroniken):** Zitiere die relevanten Stellen wörtlich mit
  Fundstelle und ordne jede einem Bauteil zu („…die capellen uff der burg…“ → Kapelle existiert, Lage offen).
- Kläre den **Zieldatum-Zustand** (`meta.date`). Bauteile jüngerer Phasen lässt du weg oder vermerkst sie.

### 2. Standort und Umgebung recherchieren
1. **Koordinaten:** Nutze die Websuche (Wikipedia/Wikidata, Denkmallisten, EBIDAT-Burgendatenbank). Wenn die
   Sandbox Netz hat, zusätzlich `python $SKILL/scripts/geo.py geocode "Burg X"`. Prüfe, ob die Koordinate
   auf der Burg liegt und nicht im Ort. Ursprung (0, 0) ist die Burgmitte.
2. **Gelände:** Wenn die Sandbox Netz hat, ein echtes Höhenmodell holen:
   `python $SKILL/scripts/geo.py terrain castle.json` (SRTM/EU-DEM/DGM, ~5–30 m Auflösung), dann
   `"terrain": {"heightmap": "heightmap.json"}`. Ohne Netz: Lage beschreiben
   (`spur`/`hilltop`/`crag`/`slope`/`lowland`/`island`) mit Relief und Richtung, abgeleitet aus Recherche
   und Abbildungen.
   Spornburg: `direction` = Kompassrichtung, in die der Sporn zeigt. Der Halsgraben liegt auf der Gegenseite.
3. **Heutige Umgebung als Rohmaterial:** `python $SKILL/scripts/geo.py osm castle.json` liefert Gewässer,
   Wald, Wege und Orte in lokalen Metern. Ohne Netz recherchierst du Lage von Fluss, Dorf, Wegen und Weinbergen
   per Websuche und Karten und skizzierst sie als Polygone.
4. **Rückprojektion auf das Zieldatum** nach `reference/umgebung.md`: Flüsse unbegradigt, Waldgrenzen,
   Rodungsinseln, Flurformen (Gewann-Streifen), Weinberge, Burgweiler, Mühlen. Lass moderne Straßen, Bahnen,
   Stauseen und Neubaugebiete weg. Alles, was aus OSM stammt und nicht historisch belegt ist, bleibt `annahme`.

### 3. `castle.json` schreiben
Schema mit allen Feldern: `reference/schema.md`. Vorlage: `$SKILL/examples/beispiel_castle.json`
(fiktiv, nur als Muster). Zum Schema:
- Koordinaten in Metern, x = Ost, y = Nord, relativ zur Burgmitte. Umrechnung von Geokoordinaten:
  `geo.py local castle.json LAT LON`.
- Elementtypen: `wall`, `tower`, `building`, `gate`, `ditch`, `bridge`.
- Jedes Element hat `evidence` mit `confidence` ∈ {gesichert, wahrscheinlich, analogie, annahme} und
  `sources` (ids). Begründe kurz in `note`.
- Fehlende Maße ergänzt du aus `reference/typologie.md` (Epoche und Region beachten). Solche Ergänzungen
  stuft du höchstens als `analogie` ein.

Dann prüfen und Fehler beheben, Warnungen bewerten:
```bash
python $SKILL/scripts/validate.py castle.json
```

### 4. Ausgaben erzeugen
```bash
# 3D: GLB (Blender, Sketchfab, Windows-3D-Viewer) + interaktiver HTML-Viewer
python $SKILL/scripts/build_model.py castle.json --glb burg.glb --html burg_3d.html
# Zeichnung aus Perspektive (SVG + PNG); Ansichten: vogelschau, nord, ost, sued, west, grundriss
python $SKILL/scripts/draw_view.py castle.json --view vogelschau -o burg_vogelschau.svg --png burg_vogelschau.png
python $SKILL/scripts/draw_view.py castle.json --azimuth 200 --elevation 18 --png burg_eigene.png  # freie Perspektive
python $SKILL/scripts/draw_view.py castle.json --view grundriss --style befund --png burg_befund.png
python $SKILL/scripts/draw_view.py castle.json --view sued --focus alles --png burg_umgebung.png    # mit Umgebung
# Quellen- und Befundbericht
python $SKILL/scripts/report.py castle.json -o bericht.md
```
Weitere Optionen: `--style feder|farbe|befund`, `--focus burg|alles|<Meter>`, `--ortho` (maßstäbliche
Parallelprojektion), `--no-env`, `--no-labels`. `--azimuth` ist die Richtung, **aus der** man schaut
(180 = von Süden).

**Selbstkontrolle (Pflicht):** Sieh dir jedes erzeugte PNG an, bevor du es übergibst. Achte auf schwebende
oder versunkene Bauteile, falsche Dachrichtungen, Mauern quer durch Gebäude, Gräben an der falschen Seite und
Bauten im Fluss. Liegt ein Plan vor, lege die Rekonstruktion darauf:
`plan.py overlay plan.png kalibrierung.json castle.json -o kontrolle.png`. Korrigiere `castle.json` und
erzeuge die Ausgaben neu.

### 5. Übergabe an den Nutzer
- Zeige die gewünschte Zeichnung bzw. den Viewer (`burg_3d.html` lässt sich direkt öffnen, im Browser
  drehen und als Bild speichern; der Knopf „Befundlage“ färbt nach Quellenlage).
- Liefere GLB und Bericht als Dateien mit.
- Fasse in wenigen Sätzen zusammen, was gesichert ist, was nach Analogie ergänzt wurde und welche
  Annahmen den größten Einfluss haben.
- Nenne konkret, welches zusätzliche Material die Unsicherheit am stärksten senken würde (z. B.
  „Urkataster 1830 für den Bachverlauf“, „Grabungsbericht zum Torbereich“).
- Wünscht der Nutzer Änderungen („Bergfried höher“, „Ansicht von Nordwest“), passe `castle.json` bzw.
  die Kameraparameter an und erzeuge neu.

## Grundsätze
- **Belegt vor plausibel vor schön.** Lieber eine schlichte Annahme mit Kennzeichnung als ein
  detailreiches Phantasiegebilde.
- Widersprechen sich Quellen, entscheide nach Quellenwert (`reference/quellenkritik.md`) und vermerke den
  Widerspruch in `note`.
- Datiere jede Bauphase (`phase`). Mische nicht unbemerkt Zustände verschiedener Jahrhunderte.
- Low-Poly ist Absicht: keine Fenster und Ornamente erfinden. Bei Bedarf Gebäude in mehrere Elemente
  teilen (z. B. Treppenturm als eigener `tower`).
- Gib bekannte Grenzen offen an. Höhenmodelle zeigen das heutige Gelände (Steinbrüche, Straßendämme,
  Aufschüttungen). Abbildungen vor 1600 sind selten maßstäblich.
