# castle.json – Schema

Alle Längen in Metern. Koordinaten `[x, y]`: x = Ost, y = Nord, Ursprung = `site.lat/lon` (Burgmitte).
Höhen von Bauteilen gelten **ab Geländeoberkante** an ihrem Standort. Fundamente werden automatisch
bis unter das Gelände verlängert, damit am Hang nichts schwebt.

```jsonc
{
  "meta": {
    "name": "Burg Beispiel",
    "date": 1350,                       // rekonstruierter Zustand (Jahr)
    "description": "kurze Einordnung",
    "sources": [
      {"id": "Q1", "type": "plan", "title": "...", "author": "...", "year": 1905, "url": "...", "note": "..."}
      // type: plan | illustration | text | map | excavation | research | analogy
    ]
  },
  "site": {
    "lat": 50.0, "lon": 8.0,            // WGS84, Burgmitte
    "elevation": 420,                   // m ü. NN (nur Information)
    "extent": 800,                      // Kantenlänge des Geländeausschnitts (100–5000)
    "resolution": 80,                   // Gitterzellen je Kante (10–250); extent/resolution ≈ 8–12 m ist gut
    "terrain": {
      "heightmap": "heightmap.json",    // ODER prozedural:
      "type": "spur",                   // spur | hilltop | crag | slope | lowland | island
      "relief": 70,                     // Höhenunterschied Burg – Tal
      "direction": 90,                  // spur: Richtung der Spornspitze; slope: Richtung des Gefälles
      "plateau_radius": 40,             // falls kein site.plateau angegeben
      "roughness": 0.3,                 // 0 = glatt … 1 = unruhig
      "seed": 7
    },
    "plateau": {                        // eingeebnete Burgfläche (Hof)
      "polygon": [[-50, -30], [60, -30], [60, 30], [-50, 30]],
      "height": null,                   // null = Mittel des Geländes darunter
      "evidence": {...}
    },
    "environment": { ... }              // siehe unten
  },
  "elements": [ ... ]                   // siehe unten
}
```

## evidence (bei jedem Element und Umgebungseintrag)
```json
{"confidence": "wahrscheinlich", "sources": ["Q1", "Q3"], "note": "Grundriss nach Q1, Höhe nach Vedute Q3"}
```
| confidence | Bedeutung | Darstellung |
|---|---|---|
| gesichert | im Bestand, Plan oder Grabung nachgewiesen | durchgezogen |
| wahrscheinlich | durch Abbildung/Text gestützt, Details ergänzt | durchgezogen |
| analogie | Gestalt von vergleichbaren Anlagen übertragen | gestrichelt, aufgehellt |
| annahme | plausible Ergänzung ohne Beleg | gepunktet, aufgehellt |

## Elemente

Gemeinsame Felder: `id` (eindeutig), `type`, `name`, `phase` (z. B. „um 1200“, „14. Jh.“),
`material`, `evidence`, optional `base` (absolute lokale Höhe der Geländeoberkante, überschreibt Gelände).

Materialien: `stone`, `stone_dark`, `sandstone`, `red_sandstone`, `brick`, `plaster`, `timber`
(Fachwerk, verputzt), `wood` – oder Hex-Farbe `"#a07050"`.
Dachmaterialien: `slate`, `tile`, `shingle`, `thatch`, `lead`, `wood`.

### wall – Mauer, Wehrmauer, Schildmauer, Zwingermauer, Palisade
```json
{"id": "ringmauer", "type": "wall", "path": [[-48, -26], [28, -32], [60, -13]], "closed": true,
 "thickness": 2.2, "height": 9, "crenellated": true, "material": "stone"}
```
Palisade: `"material": "wood", "thickness": 0.5, "crenellated": false`.
Schildmauer: `thickness` 3–5, `height` 15–25.

### tower – Bergfried, Flankenturm, Schalenturm, Wohnturm
```json
{"id": "bergfried", "type": "tower", "shape": "square", "center": [-34, -6], "size": 11,
 "orientation": 0, "height": 28, "roof": "pyramid", "roof_height": 9, "roof_material": "slate"}
```
- `shape`: `round` (mit `radius`, `segments` = 12) | `square` (mit `size` = Zahl oder `[Länge, Breite]`
  und `orientation` in Grad) | beliebig über `polygon`.
- `roof`: `cone` | `pyramid` | `hip` | `gable` | `shed` | `flat` | `crenellated` (Zinnenkranz) | `none`.
- `roof_height` optional (sonst automatisch).

### building – Palas, Kemenate, Kapelle, Wirtschaftsbau, Vorburgbauten
```json
{"id": "palas", "type": "building", "polygon": [[-12, -29], [24, -32], [25, -19], [-11, -16]],
 "height": 13, "roof": "gable", "ridge_direction": 85, "roof_material": "tile"}
```
Statt `polygon` geht auch `center` + `size: [Länge, Breite]` + `orientation` (Richtung der Länge).
`height` = Traufhöhe über Gelände. `ridge_direction` (Kompassgrad) ist optional; Standard ist die längste Kante.

### gate – Torhaus, Torturm
```json
{"id": "torhaus", "type": "gate", "center": [-48, 11], "size": [10, 8], "orientation": 90,
 "height": 13, "roof": "hip", "passage_width": 3.2, "passage_height": 4.2}
```
Die Durchfahrt verläuft entlang `orientation`, also quer durch die Mauer.

### ditch – Halsgraben, Ringgraben, Wassergraben
```json
{"id": "halsgraben", "type": "ditch", "path": [[-63, -90], [-62, 0], [-63, 90]], "width": 16, "depth": 8,
 "closed": false, "water": false}
```
`water: true` füllt den Graben (Wasserburg), optional mit `water_level`.

### bridge – Brücke, Zugbrückenauflager
```json
{"id": "bruecke", "type": "bridge", "path": [[-76, 11], [-53, 11]], "width": 3.5, "deck_height": null, "piers": 2}
```

## Umgebung (`site.environment`)
```jsonc
{
  "rivers":      [{"name": "Bach", "path": [[x, y], ...], "width": 16, "depth": 2, "level": null, "evidence": {...}}],
  "water":       [{"name": "Weiher", "polygon": [...], "level": null, "evidence": {...}}],
  "roads":       [{"name": "Burgweg", "path": [...], "width": 4, "evidence": {...}}],
  "settlements": [{"name": "Dorf", "polygon": [...], "houses": 16, "church": true, "church_orientation": 90,
                   "material": "timber", "roof_material": "thatch", "evidence": {...}}],
  "fields":      [{"kind": "acker", "polygon": [...], "strip_width": 14, "evidence": {...}}],
                   // kind: acker (Streifenflur) | wiese | weide | weinberg | garten
  "forest":      [{"kind": "laub", "density": 0.6, "polygon": [...], "evidence": {...}}],
                   // kind: laub | nadel | misch; density 0–1
  "max_trees": 2500
}
```
Reihenfolge der Färbung: Flur → Wald → Siedlung → Wege → Gewässer (spätere überdecken frühere).
Flüsse fallen in Fließrichtung des `path` nie an, das Wasser folgt dem tiefsten Punkt.
Gib den `path` deshalb **flussabwärts** an.
